from __future__ import annotations

from pathlib import Path

from appliance_agent.flow_engine import FlowEngine
from appliance_agent.guardrail import Guardrail
from appliance_agent.ingestion import build_chunks, load_safety_rules
from appliance_agent.models import ChatResponse, DiagnosisState, RetrievedDoc
from appliance_agent.retrieval import HybridRetriever
from appliance_agent.text import extract_fault_code, extract_model, unique_preserve_order


class ApplianceAgent:
    def __init__(self, retriever: HybridRetriever, guardrail: Guardrail, flow_engine: FlowEngine):
        self.retriever = retriever
        self.guardrail = guardrail
        self.flow_engine = flow_engine
        self.sessions: dict[str, DiagnosisState] = {}

    @classmethod
    def from_data_dir(cls, data_dir: str | Path) -> "ApplianceAgent":
        chunks = build_chunks(data_dir)
        safety_rules = load_safety_rules(data_dir)
        return cls(
            retriever=HybridRetriever(chunks),
            guardrail=Guardrail(safety_rules),
            flow_engine=FlowEngine.from_data_dir(data_dir),
        )

    def chat(self, session_id: str, user_input: str) -> ChatResponse:
        guardrail_result = self.guardrail.check_user_input(user_input)
        if guardrail_result.risk != "none":
            return ChatResponse(
                answer=self.guardrail.safety_reply(guardrail_result),
                intent="safety",
                contexts=[],
                citations=[],
                metadata={"risk": guardrail_result.risk, "signal": guardrail_result.signal},
            )

        active_state = self.sessions.get(session_id)
        if active_state and not active_state.done and not self._looks_like_new_topic(user_input):
            step = self.flow_engine.next_action(active_state, user_input)
            return ChatResponse(
                answer=self._format_step(step.payload, step.kind),
                intent="diagnose",
                contexts=[],
                citations=[],
                metadata={"flow_id": active_state.flow_id, "step_kind": step.kind},
            )

        model = extract_model(user_input)
        fault_code = extract_fault_code(user_input)
        intent = self._classify_intent(user_input, fault_code)

        if intent == "diagnose":
            if fault_code:
                results = self._diagnosis_results(user_input, model, fault_code)
                return self._fault_code_response(user_input, model, fault_code, results)
            flow_id = self.flow_engine.select_flow(user_input)
            state = self.flow_engine.create_state(flow_id)
            self.sessions[session_id] = state
            return ChatResponse(
                answer=self._format_step(state.pending_question or "请补充故障现象。", "ask"),
                intent="diagnose",
                contexts=[],
                citations=[],
                metadata={"flow_id": flow_id, "step_kind": "ask"},
            )

        if intent == "warranty_fee":
            results = self.retriever.search_policy(user_input, model=model, top_k=5)
            return self._policy_response(user_input, model, results)

        if intent == "qa":
            results = self._qa_results(user_input, model)
            return self._qa_response(user_input, results)

        return ChatResponse(
            answer="你好，我可以帮你查询 Aqualink 洗衣机的使用、维护、故障码、保修和收费问题。",
            intent="chitchat",
            contexts=[],
            citations=[],
        )

    def _classify_intent(self, text: str, fault_code: str | None) -> str:
        if any(word in text for word in ["保修", "收费", "费用", "免费", "退货", "换货", "安装", "发票", "凭证"]):
            return "warranty_fee"
        if fault_code or any(
            word in text
            for word in ["不排水", "排水慢", "不脱水", "不进水", "进水慢", "漏水", "门打不开", "噪音", "震动", "烘干", "烘不干", "故障码"]
        ):
            return "diagnose"
        if any(word in text for word in ["怎么", "如何", "能不能", "使用", "清理", "维护", "童锁", "水位", "程序"]):
            return "qa"
        return "chitchat"

    def _looks_like_new_topic(self, text: str) -> bool:
        return bool(extract_fault_code(text)) or any(word in text for word in ["保修", "收费", "换货", "退货"])

    def _diagnosis_results(self, query: str, model: str | None, fault_code: str) -> list[RetrievedDoc]:
        results = self.retriever.search_fault_code(query, model=model, fault_code=fault_code, top_k=4)
        if model:
            results.extend(self.retriever.search_manual(query, model=model, top_k=2))
        results.extend(self.retriever.search_tickets(query, model=model, top_k=2))
        return _dedupe_results(results)

    def _qa_results(self, query: str, model: str | None) -> list[RetrievedDoc]:
        results = []
        results.extend(self.retriever.search_faq(query, model=model, top_k=3))
        results.extend(self.retriever.search_manual(query, model=model, top_k=3))
        return _dedupe_results(results)[:5]

    def _fault_code_response(
        self,
        query: str,
        model: str | None,
        fault_code: str,
        results: list[RetrievedDoc],
    ) -> ChatResponse:
        if not results:
            return ChatResponse(
                answer="暂时没有检索到足够资料。建议停止异常程序并转人工确认。",
                intent="diagnose",
                contexts=[],
                citations=[],
            )

        primary = results[0]
        citations = [result.doc_id for result in results[:4]]
        model_text = f"{model} " if model else ""
        answer = (
            f"{model_text}{fault_code} 相关资料显示：{_compact(primary.text)}\n\n"
            "建议先做用户可触达的外部检查，并在清理过滤器、移动管路前先断电。"
            "如果自检后仍反复报错、伴随异响/焦味/漏水，停止使用并报修。"
            f"\n【依据：{'、'.join(citations)}】"
        )
        return ChatResponse(
            answer=answer,
            intent="diagnose",
            contexts=[result.text for result in results[:4]],
            citations=citations,
            metadata={"model": model, "fault_code": fault_code},
        )

    def _policy_response(self, query: str, model: str | None, results: list[RetrievedDoc]) -> ChatResponse:
        citations = [result.doc_id for result in results[:5]]
        context = "\n".join(result.text for result in results[:5])
        answer = (
            f"{model + ' ' if model else ''}售后政策口径：主要部件通常保修 3 年，排水泵/排水阀属于主要部件范围；"
            "但是否免费需要同时确认购买凭证、购买日期、使用场景、是否人为拆修，以及售后检测结论。"
            "如果检测为保内质量故障，一般不收对应保内维修费用；如果属于安装、堵塞、使用不当或人为原因，可能产生上门、人工或配件费用。"
            "客服不能仅凭描述承诺免费，也不能给最终金额。"
        )
        if citations:
            answer += f"\n【依据：{'、'.join(citations)}】"
        return ChatResponse(
            answer=answer,
            intent="warranty_fee",
            contexts=[context] if context else [],
            citations=citations,
            metadata={"model": model},
        )

    def _qa_response(self, query: str, results: list[RetrievedDoc]) -> ChatResponse:
        if not results:
            return ChatResponse(
                answer="暂时没有找到足够资料。请补充型号或具体现象，我再帮你查。",
                intent="qa",
                contexts=[],
                citations=[],
            )
        citations = [result.doc_id for result in results[:3]]
        answer = f"{_compact(results[0].text)}\n【依据：{'、'.join(citations)}】"
        return ChatResponse(
            answer=answer,
            intent="qa",
            contexts=[result.text for result in results[:3]],
            citations=citations,
        )

    def _format_step(self, payload: str, kind: str) -> str:
        if kind == "ask":
            return f"为了安全准确排查，请先确认：{payload}"
        if kind == "escalate":
            return f"{payload} 请关闭水龙头并断电，联系官方售后。"
        return f"建议：{payload}"


def _compact(text: str, limit: int = 360) -> str:
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"


def _dedupe_results(results: list[RetrievedDoc]) -> list[RetrievedDoc]:
    seen: set[str] = set()
    deduped: list[RetrievedDoc] = []
    for result in results:
        if result.doc_id not in seen:
            seen.add(result.doc_id)
            deduped.append(result)
    ordered_ids = unique_preserve_order(result.doc_id for result in deduped)
    by_id = {result.doc_id: result for result in deduped}
    return [by_id[doc_id] for doc_id in ordered_ids]

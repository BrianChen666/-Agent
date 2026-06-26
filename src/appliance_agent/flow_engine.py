from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from appliance_agent.models import DiagnosisState, StepResult


class FlowEngine:
    def __init__(self, flows: list[dict[str, Any]], global_rules: list[str] | None = None):
        self.flows = {flow["flow_id"]: flow for flow in flows}
        self.global_rules = global_rules or []

    @classmethod
    def from_data_dir(cls, data_dir: str | Path) -> "FlowEngine":
        path = Path(data_dir) / "flows" / "troubleshooting_flow_tree.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(data.get("flows", []), data.get("global_rules", []))

    def select_flow(self, user_issue: str) -> str:
        rules = [
            ("F_DRAIN", ["不排水", "排水慢", "E2", "积水"]),
            ("F_NO_SPIN", ["不脱水", "脱水", "E10", "偏载"]),
            ("F_INLET", ["不进水", "进水慢", "E1"]),
            ("F_DOOR_LOCK", ["门打不开", "门锁", "上盖锁", "E3", "E13"]),
            ("F_LEAK", ["漏水", "机底有水", "LE"]),
            ("F_NOISE", ["噪音", "震动", "撞桶"]),
            ("F_DRYING", ["烘干", "烘不干", "潮湿"]),
        ]
        for flow_id, keywords in rules:
            if flow_id in self.flows and any(keyword in user_issue for keyword in keywords):
                return flow_id
        return "F_NO_SPIN" if "F_NO_SPIN" in self.flows else next(iter(self.flows))

    def start(self, flow_id: str) -> StepResult:
        flow = self.flows[flow_id]
        question = flow.get("entry_questions", ["请描述一下具体故障现象。"])[0]
        return StepResult("ask", question, flow_done=False)

    def create_state(self, flow_id: str) -> DiagnosisState:
        state = DiagnosisState(flow_id=flow_id)
        first = self.start(flow_id)
        state.pending_question = first.payload
        return state

    def next_action(self, state: DiagnosisState, user_answer: str | None) -> StepResult:
        flow = self.flows[state.flow_id]
        if user_answer and state.pending_question:
            state.answers[state.pending_question] = user_answer
        if user_answer and self._matches_escalation(flow, user_answer):
            state.done = True
            return StepResult("escalate", "出现高风险或需专业处理的信号，建议停止使用并报修。", True)

        questions = flow.get("entry_questions", [])
        next_index = state.question_index + 1
        if next_index < len(questions):
            state.question_index = next_index
            state.pending_question = questions[next_index]
            return StepResult("ask", questions[next_index], False)

        state.done = True
        action = self._first_safe_action(flow)
        return StepResult("advise", action, True)

    def _matches_escalation(self, flow: dict[str, Any], text: str) -> bool:
        return any(signal in text for signal in flow.get("escalation", [])) or any(
            keyword in text for keyword in ["焦味", "跳闸", "冒烟", "机底持续漏水"]
        )

    def _first_safe_action(self, flow: dict[str, Any]) -> str:
        for step in flow.get("steps", []):
            for branch in step.get("branches", []):
                if branch.get("action"):
                    return branch["action"]
                if branch.get("next"):
                    return branch["next"]
        return "资料不足以继续自助排查，建议转人工或预约售后。"

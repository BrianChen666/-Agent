from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from appliance_agent.models import Chunk
from appliance_agent.text import extract_fault_code, slugify, unique_preserve_order

ALL_MODELS = ["X100", "X200", "W80"]


def load_safety_rules(data_dir: str | Path) -> str:
    path = Path(data_dir) / "policies" / "safety_boundaries.md"
    return path.read_text(encoding="utf-8")


def build_chunks(data_dir: str | Path) -> list[Chunk]:
    data_path = Path(data_dir)
    chunks: list[Chunk] = []
    chunks.extend(_load_faq(data_path))
    chunks.extend(_load_fault_codes(data_path))
    chunks.extend(_load_reference_issues(data_path))
    chunks.extend(_load_manuals(data_path))
    chunks.extend(_load_policy(data_path))
    chunks.extend(_load_fee_rules(data_path))
    chunks.extend(_load_tickets(data_path))
    return chunks


def _metadata(
    *,
    source_type: str,
    model: list[str],
    fault_code: str | None,
    category: str | None,
    severity: str | None,
    doc_id: str,
    source_file: str,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "model": model,
        "fault_code": fault_code,
        "category": category,
        "severity": severity,
        "doc_id": doc_id,
        "source_file": source_file.replace("\\", "/"),
    }


def _relative(data_dir: Path, path: Path) -> str:
    return path.relative_to(data_dir).as_posix()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_faq(data_dir: Path) -> list[Chunk]:
    path = data_dir / "faq" / "faq.jsonl"
    chunks: list[Chunk] = []
    for row in _load_jsonl(path):
        doc_id = row["faq_id"]
        text = "\n".join(
            [
                f"问：{row.get('question', '')}",
                f"答：{row.get('answer', '')}",
                f"升级条件：{row.get('escalation', '')}",
                "标签：" + "、".join(row.get("tags", [])),
            ]
        )
        chunks.append(
            Chunk(
                text=text,
                doc_id=doc_id,
                metadata=_metadata(
                    source_type="faq",
                    model=row.get("applies_to", ALL_MODELS),
                    fault_code=extract_fault_code(text),
                    category=row.get("category"),
                    severity=None,
                    doc_id=doc_id,
                    source_file=_relative(data_dir, path),
                ),
            )
        )
    return chunks


def _load_fault_codes(data_dir: Path) -> list[Chunk]:
    path = data_dir / "knowledge_base" / "fault_codes.yaml"
    data = _load_yaml(path)
    chunks: list[Chunk] = []
    for row in data.get("fault_codes", []):
        code = str(row["code"]).upper()
        doc_id = f"FC-{code}"
        lines = [
            f"故障码：{code}",
            f"含义：{row.get('meaning', '')}",
            "常见原因：" + "；".join(row.get("common_causes", [])),
            "用户可自检：" + "；".join(row.get("user_self_check", [])),
            "禁止操作：" + "；".join(row.get("do_not", [])),
            "报修条件：" + "；".join(row.get("report_conditions", [])),
            "相关流程：" + "、".join(row.get("related_flows", [])),
        ]
        chunks.append(
            Chunk(
                text="\n".join(lines),
                doc_id=doc_id,
                metadata=_metadata(
                    source_type="fault_code",
                    model=row.get("models", ALL_MODELS),
                    fault_code=code,
                    category="故障码",
                    severity=row.get("severity"),
                    doc_id=doc_id,
                    source_file=_relative(data_dir, path),
                ),
            )
        )
    return chunks


def _load_reference_issues(data_dir: Path) -> list[Chunk]:
    path = data_dir / "knowledge_base" / "reference_based_common_issues.yaml"
    data = _load_yaml(path)
    chunks: list[Chunk] = []
    for row in data.get("issues", []):
        doc_id = row["issue_id"]
        text = "\n".join(
            [
                f"问题：{row.get('issue_name', '')}",
                "公开常见代码：" + "；".join(row.get("real_world_codes_seen", [])),
                f"共性含义：{row.get('common_meaning', '')}",
                "常见原因：" + "；".join(row.get("common_causes", [])),
                "用户可检查：" + "；".join(row.get("user_can_check", [])),
                "用户禁止操作：" + "；".join(row.get("user_must_not_do", [])),
                "需要售后：" + "；".join(row.get("service_when", [])),
            ]
        )
        chunks.append(
            Chunk(
                text=text,
                doc_id=doc_id,
                metadata=_metadata(
                    source_type="ref",
                    model=row.get("models", ALL_MODELS),
                    fault_code=extract_fault_code(text),
                    category="故障码",
                    severity=None,
                    doc_id=doc_id,
                    source_file=_relative(data_dir, path),
                ),
            )
        )
    return chunks


def _load_manuals(data_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted((data_dir / "manuals").glob("*.md")):
        model = path.name.split("_", 1)[0].upper()
        content = path.read_text(encoding="utf-8")
        sections = _split_markdown_sections(content)
        for index, (title, body) in enumerate(sections):
            text = f"型号：{model}\n章节：{title}\n{body.strip()}"
            for part_index, part in enumerate(_split_long_text(text, 800, 80)):
                suffix = index if len(part) == len(text) else f"{index}-{part_index}"
                doc_id = f"MAN-{model}-{slugify(title)}-{suffix}"
                chunks.append(
                    Chunk(
                        text=part,
                        doc_id=doc_id,
                        metadata=_metadata(
                            source_type="manual",
                            model=[model],
                            fault_code=extract_fault_code(part),
                            category=_manual_category(title),
                            severity=None,
                            doc_id=doc_id,
                            source_file=_relative(data_dir, path),
                        ),
                    )
                )
    return chunks


def _load_policy(data_dir: Path) -> list[Chunk]:
    path = data_dir / "policies" / "after_sales_policy.md"
    content = path.read_text(encoding="utf-8")
    chunks: list[Chunk] = []
    for index, (title, body) in enumerate(_split_markdown_sections(content)):
        text = f"政策章节：{title}\n{body.strip()}"
        doc_id = f"POL-{slugify(title)}-{index}"
        chunks.append(
            Chunk(
                text=text,
                doc_id=doc_id,
                metadata=_metadata(
                    source_type="policy",
                    model=ALL_MODELS,
                    fault_code=extract_fault_code(text),
                    category=_policy_category(title),
                    severity=None,
                    doc_id=doc_id,
                    source_file=_relative(data_dir, path),
                ),
            )
        )
    return chunks


def _load_fee_rules(data_dir: Path) -> list[Chunk]:
    path = data_dir / "policies" / "service_fee_rules.yaml"
    data = _load_yaml(path)
    chunks: list[Chunk] = []
    index = 0
    for row in data.get("fee_components", []):
        index += 1
        doc_id = f"FEE-{index}"
        text = "\n".join(
            [
                f"费用项：{row.get('component', '')}",
                f"含义：{row.get('meaning', '')}",
                "可能适用：" + "；".join(row.get("when_may_apply", [])),
                f"客服规则：{row.get('agent_rule', '')}",
            ]
        )
        chunks.append(_fee_chunk(data_dir, path, doc_id, text))
    for row in data.get("charge_decision_rules", []):
        index += 1
        doc_id = row.get("rule_id") or f"FEE-{index}"
        text = "\n".join(
            [
                f"规则：{doc_id}",
                f"场景：{row.get('situation', '')}",
                f"建议回复：{row.get('recommended_reply', '')}",
            ]
        )
        chunks.append(_fee_chunk(data_dir, path, doc_id, text))
    return chunks


def _fee_chunk(data_dir: Path, path: Path, doc_id: str, text: str) -> Chunk:
    return Chunk(
        text=text,
        doc_id=doc_id,
        metadata=_metadata(
            source_type="fee",
            model=ALL_MODELS,
            fault_code=extract_fault_code(text),
            category="收费",
            severity=None,
            doc_id=doc_id,
            source_file=_relative(data_dir, path),
        ),
    )


def _load_tickets(data_dir: Path) -> list[Chunk]:
    path = data_dir / "tickets" / "historical_tickets.jsonl"
    chunks: list[Chunk] = []
    for row in _load_jsonl(path):
        doc_id = row["ticket_id"]
        text = "\n".join(
            [
                f"用户问题：{row.get('user_issue', '')}",
                "客服追问：" + "；".join(row.get("agent_follow_up", [])),
                "用户反馈：" + "；".join(row.get("user_feedback", [])),
                f"自检结果：{row.get('self_check_result', '')}",
                f"最终动作：{row.get('final_action', '')}",
                f"结果：{row.get('result', '')}",
                "相关知识：" + "、".join(row.get("related_knowledge", [])),
                f"安全边界：{row.get('safety_boundary', '')}",
            ]
        )
        chunks.append(
            Chunk(
                text=text,
                doc_id=doc_id,
                metadata=_metadata(
                    source_type="ticket",
                    model=[row.get("model")] if row.get("model") else ALL_MODELS,
                    fault_code=(row.get("fault_code") or extract_fault_code(text) or None),
                    category=row.get("category"),
                    severity=None,
                    doc_id=doc_id,
                    source_file=_relative(data_dir, path),
                ),
            )
        )
    return chunks


def _split_markdown_sections(content: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+)$", content, flags=re.M))
    if not matches:
        return [("全文", content)]
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections.append((match.group(1).strip(), content[start:end].strip()))
    return sections


def _split_long_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return parts


def _manual_category(title: str) -> str | None:
    mapping = {
        "异常": "故障码",
        "维护": "日常维护",
        "功能": "使用入门",
        "模式": "使用入门",
        "禁止": "安全",
    }
    return _map_category(title, mapping)


def _policy_category(title: str) -> str | None:
    mapping = {
        "保修": "保修",
        "收费": "收费",
        "检测费": "收费",
        "安装": "安装",
        "退换货": "退换货",
        "发票": "凭证",
    }
    return _map_category(title, mapping)


def _map_category(title: str, mapping: dict[str, str]) -> str | None:
    hits = [value for key, value in mapping.items() if key in title]
    return unique_preserve_order(hits)[0] if hits else title

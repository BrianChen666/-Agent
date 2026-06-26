from __future__ import annotations

import json
from pathlib import Path


def build_golden(data_dir: str | Path, output_path: str | Path) -> int:
    data_path = Path(data_dir)
    output = Path(output_path)
    rows: list[dict[str, object]] = []

    for line in (data_path / "faq" / "faq.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        rows.append(
            {
                "query": item["question"],
                "expected_doc_ids": [item["faq_id"]],
                "source": "faq",
                "expected_answer": item["answer"],
            }
        )

    for line in (data_path / "tickets" / "historical_tickets.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        expected = [f"FC-{code}" if code.startswith(("E", "F")) or code in {"PF", "LE"} else code for code in item.get("related_knowledge", [])]
        rows.append(
            {
                "query": item["user_issue"],
                "expected_doc_ids": expected,
                "source": "ticket",
                "expected_action": item.get("final_action"),
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[1]
    count = build_golden(project_root / "原始数据", project_root / "evaluation" / "golden_set" / "golden.jsonl")
    print(f"wrote {count} golden cases")

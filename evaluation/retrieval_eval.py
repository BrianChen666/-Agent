from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliance_agent.ingestion import build_chunks
from appliance_agent.retrieval import HybridRetriever


def evaluate_retrieval(data_dir: str | Path, golden_path: str | Path, top_k: int = 5) -> dict[str, float]:
    retriever = HybridRetriever(build_chunks(data_dir))
    cases = [json.loads(line) for line in Path(golden_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = 0
    reciprocal_sum = 0.0
    for case in cases:
        expected = set(case["expected_doc_ids"])
        results = retriever.hybrid_search(case["query"], top_k=top_k)
        doc_ids = [result.doc_id for result in results]
        if expected & set(doc_ids):
            hits += 1
            ranks = [doc_ids.index(doc_id) + 1 for doc_id in expected if doc_id in doc_ids]
            reciprocal_sum += 1.0 / min(ranks)
    total = max(len(cases), 1)
    return {"cases": float(len(cases)), f"hit_rate@{top_k}": hits / total, "mrr": reciprocal_sum / total}


if __name__ == "__main__":
    metrics = evaluate_retrieval(
        PROJECT_ROOT / "原始数据",
        PROJECT_ROOT / "evaluation" / "golden_set" / "golden.jsonl",
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

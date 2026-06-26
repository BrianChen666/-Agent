from appliance_agent.ingestion import build_chunks
from appliance_agent.retrieval import HybridRetriever


def test_fault_code_search_prioritizes_exact_code_and_model(DATA_DIR):
    retriever = HybridRetriever(build_chunks(DATA_DIR))

    results = retriever.hybrid_search(
        "X100 显示 E2 不排水怎么办",
        model="X100",
        fault_code="E2",
        source_types=["fault_code", "ref"],
        top_k=3,
    )

    assert results
    assert results[0].doc_id == "FC-E2"
    assert all("X100" in result.metadata["model"] for result in results)
    assert {result.metadata["source_type"] for result in results} <= {"fault_code", "ref"}


def test_policy_search_returns_warranty_and_fee_sources(DATA_DIR):
    retriever = HybridRetriever(build_chunks(DATA_DIR))

    results = retriever.search_policy("X200 排水泵坏了还在三年内收费吗", model="X200", top_k=5)

    assert any(result.metadata["source_type"] == "policy" for result in results)
    assert any(result.metadata["source_type"] == "fee" for result in results)
    assert any("主要部件保修 3 年" in result.text for result in results)

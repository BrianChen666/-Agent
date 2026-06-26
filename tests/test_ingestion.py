from appliance_agent.ingestion import build_chunks, load_safety_rules


def test_build_chunks_creates_source_specific_metadata(DATA_DIR):
    chunks = build_chunks(DATA_DIR)
    by_id = {chunk.doc_id: chunk for chunk in chunks}

    assert "Q-001" in by_id
    assert "FC-E2" in by_id
    assert "REF-DRAIN-01" in by_id
    assert "T-001" in by_id
    assert any(chunk.metadata["source_type"] == "manual" for chunk in chunks)
    assert all("safety_boundaries.md" not in chunk.metadata["source_file"] for chunk in chunks)

    e2 = by_id["FC-E2"]
    assert e2.metadata["fault_code"] == "E2"
    assert set(e2.metadata["model"]) == {"X100", "X200", "W80"}
    assert e2.metadata["category"] == "故障码"
    assert "不得拆卸排水泵" in e2.text


def test_load_safety_rules_keeps_guardrail_source_outside_retrieval(DATA_DIR):
    rules = load_safety_rules(DATA_DIR)

    assert "拆卸排水泵" in rules
    assert "短接门锁" in rules

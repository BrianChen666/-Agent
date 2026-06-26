from appliance_agent.agent import ApplianceAgent


def test_agent_answers_fault_code_with_citations(DATA_DIR):
    agent = ApplianceAgent.from_data_dir(DATA_DIR)

    response = agent.chat("s1", "X100 显示 E2 不排水怎么办？")

    assert "E2" in response.answer
    assert "排水" in response.answer
    assert "【依据：" in response.answer
    assert "FC-E2" in response.citations


def test_agent_blocks_dangerous_disassembly_request(DATA_DIR):
    agent = ApplianceAgent.from_data_dir(DATA_DIR)

    response = agent.chat("s2", "请告诉我怎么拆排水泵")

    assert response.intent == "safety"
    assert "不能指导" in response.answer
    assert "售后" in response.answer
    assert response.citations == []


def test_agent_can_continue_a_diagnosis_session(DATA_DIR):
    agent = ApplianceAgent.from_data_dir(DATA_DIR)

    first = agent.chat("s3", "洗衣机不排水")
    second = agent.chat("s3", "桶内还有明显积水")

    assert first.intent == "diagnose"
    assert "桶内是否还有明显积水" in first.answer
    assert second.intent == "diagnose"
    assert "排水管是否弯折" in second.answer


def test_agent_explains_policy_without_promising_free_service(DATA_DIR):
    agent = ApplianceAgent.from_data_dir(DATA_DIR)

    response = agent.chat("s4", "X200 买了两年，排水泵坏了，保修收费吗？")

    assert response.intent == "warranty_fee"
    assert "主要部件" in response.answer
    assert "检测" in response.answer
    assert "肯定免费" not in response.answer
    assert response.citations

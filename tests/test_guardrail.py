from appliance_agent.guardrail import Guardrail
from appliance_agent.ingestion import load_safety_rules


def test_guardrail_detects_forbidden_repair_steps(DATA_DIR):
    guardrail = Guardrail(load_safety_rules(DATA_DIR))

    result = guardrail.check_user_input("教我怎么拆排水泵，最好能短接门锁继续运行")

    assert result.risk == "forbidden_request"
    assert "拆排水泵" in result.signal or "短接门锁" in result.signal


def test_guardrail_detects_high_risk_signal(DATA_DIR):
    guardrail = Guardrail(load_safety_rules(DATA_DIR))

    result = guardrail.check_user_input("洗衣机漏水后还跳闸，有焦糊味")

    assert result.risk == "high_signal"
    assert result.signal

from __future__ import annotations

from appliance_agent.models import GuardrailResult


class Guardrail:
    def __init__(self, safety_rules: str):
        self.safety_rules = safety_rules
        self.forbidden_keywords = [
            "拆排水泵",
            "拆卸排水泵",
            "拆主板",
            "打开底部电路",
            "短接门锁",
            "绕过水位保护",
            "测强电",
            "强拉机门",
            "私自拆修",
            "拆电机",
            "拆加热管",
        ]
        self.high_signal_keywords = [
            "冒烟",
            "焦味",
            "焦糊味",
            "跳闸",
            "触电",
            "麻手",
            "机底持续漏水",
            "持续漏水",
            "漏水后还跳闸",
            "门锁30分钟",
            "门锁 30 分钟",
            "无法释放超过 30 分钟",
        ]

    def check_user_input(self, user_input: str) -> GuardrailResult:
        for keyword in self.forbidden_keywords:
            if keyword in user_input:
                return GuardrailResult("forbidden_request", keyword)
        for keyword in self.high_signal_keywords:
            if keyword in user_input:
                return GuardrailResult("high_signal", keyword)
        if "漏水" in user_input and ("跳闸" in user_input or "焦" in user_input):
            return GuardrailResult("high_signal", "漏水伴随电气异常")
        return GuardrailResult("none", None)

    def safety_reply(self, result: GuardrailResult) -> str:
        if result.risk == "forbidden_request":
            return (
                f"这个操作涉及{result.signal or '拆机或电气风险'}，我不能指导。"
                "请停止自行拆修，保持断电，联系官方售后或转人工处理。"
            )
        if result.risk == "high_signal":
            return (
                f"已识别到高风险信号：{result.signal or '电气或漏水异常'}。"
                "请立即停止使用，关闭水龙头并断开电源，避免接触积水区域，建议直接报修或转人工。"
            )
        return ""

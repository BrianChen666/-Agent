from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from appliance_agent.agent import ApplianceAgent


def main() -> None:
    agent = ApplianceAgent.from_data_dir(PROJECT_ROOT / "原始数据")
    session_id = "cli"
    print("Aqualink 售后 Agent，输入 exit 退出。")
    while True:
        message = input("用户> ").strip()
        if message.lower() in {"exit", "quit"}:
            break
        response = agent.chat(session_id, message)
        print(f"客服> {response.answer}")


if __name__ == "__main__":
    main()

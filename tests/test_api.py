from fastapi.testclient import TestClient

from appliance_agent.api.app import create_app


def test_root_serves_chat_page():
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Aqualink" in response.text
    assert "/chat" in response.text
    assert "在线客服" in response.text

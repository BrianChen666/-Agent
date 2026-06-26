from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from appliance_agent.agent import ApplianceAgent


class ChatRequest(BaseModel):
    session_id: str = Field(default="default")
    message: str


class SearchRequest(BaseModel):
    query: str
    model: str | None = None
    fault_code: str | None = None
    source_types: list[str] | None = None
    top_k: int = 5


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Aqualink 在线客服 Agent</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17211c;
      --muted: #65736d;
      --line: #d9e3dc;
      --paper: #f7faf6;
      --panel: #ffffff;
      --accent: #117865;
      --accent-dark: #0a4f42;
      --warn: #b3541e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        linear-gradient(90deg, rgba(17,120,101,.07) 1px, transparent 1px),
        linear-gradient(180deg, rgba(17,120,101,.05) 1px, transparent 1px),
        var(--paper);
      background-size: 32px 32px;
      font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif;
    }
    main {
      width: min(1180px, calc(100vw - 32px));
      min-height: 100vh;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 330px 1fr;
      gap: 22px;
      padding: 28px 0;
    }
    aside, section {
      background: rgba(255,255,255,.92);
      border: 1px solid var(--line);
      box-shadow: 0 20px 60px rgba(23,33,28,.09);
    }
    aside {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      border-radius: 8px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 800;
      letter-spacing: 0;
      font-size: 20px;
    }
    .mark {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: white;
      background: radial-gradient(circle at 35% 30%, #4fc3a8, var(--accent-dark));
      font-weight: 900;
    }
    .status {
      border-left: 4px solid var(--accent);
      padding: 12px 14px;
      background: #eef7f3;
      color: var(--accent-dark);
      line-height: 1.55;
      font-size: 14px;
    }
    .quick {
      display: grid;
      gap: 10px;
    }
    .quick button {
      border: 1px solid var(--line);
      background: #fbfdfb;
      padding: 11px 12px;
      border-radius: 6px;
      text-align: left;
      color: var(--ink);
      cursor: pointer;
    }
    .quick button:hover { border-color: var(--accent); }
    .links {
      margin-top: auto;
      display: grid;
      gap: 8px;
      font-size: 14px;
    }
    a { color: var(--accent-dark); font-weight: 700; }
    section {
      border-radius: 8px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      overflow: hidden;
    }
    header {
      padding: 22px 24px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: center;
    }
    h1 {
      margin: 0 0 6px;
      font-size: 24px;
      line-height: 1.2;
    }
    header p {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
    }
    .badge {
      white-space: nowrap;
      border: 1px solid #f0c596;
      color: var(--warn);
      background: #fff7ed;
      border-radius: 999px;
      padding: 8px 11px;
      font-size: 13px;
    }
    #messages {
      padding: 24px;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: 440px;
      max-height: calc(100vh - 220px);
    }
    .msg {
      width: min(760px, 100%);
      padding: 14px 16px;
      border-radius: 8px;
      line-height: 1.65;
      white-space: pre-wrap;
    }
    .user {
      align-self: flex-end;
      background: var(--accent);
      color: white;
    }
    .bot {
      align-self: flex-start;
      background: #f4f8f5;
      border: 1px solid var(--line);
    }
    .meta {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    form {
      border-top: 1px solid var(--line);
      padding: 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      background: #fbfdfb;
    }
    input {
      min-height: 48px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 14px;
      font: inherit;
    }
    input:focus {
      outline: 2px solid rgba(17,120,101,.22);
      border-color: var(--accent);
    }
    form button {
      min-width: 104px;
      border: 0;
      border-radius: 6px;
      background: var(--accent-dark);
      color: white;
      font-weight: 800;
      cursor: pointer;
    }
    form button:disabled {
      opacity: .6;
      cursor: wait;
    }
    @media (max-width: 820px) {
      main { grid-template-columns: 1fr; }
      aside { order: 2; }
      #messages { max-height: none; }
      form { grid-template-columns: 1fr; }
      form button { min-height: 46px; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main>
    <aside>
      <div class="brand"><div class="mark">A</div><div>Aqualink<br />售后 Agent</div></div>
      <div class="status">已连接本地知识库。支持故障码、排障、保修收费、说明书和安全边界查询。</div>
      <div class="quick">
        <button type="button" data-q="X100 显示 E2 不排水怎么办？">X100 显示 E2 不排水怎么办？</button>
        <button type="button" data-q="X200 买了两年，排水泵坏了，保修收费吗？">X200 排水泵保修收费吗？</button>
        <button type="button" data-q="请告诉我怎么拆排水泵">危险请求拦截测试</button>
      </div>
      <div class="links">
        <a href="/docs">打开 API 文档</a>
        <a href="/health">查看健康检查</a>
      </div>
    </aside>
    <section>
      <header>
        <div>
          <h1>在线客服工作台</h1>
          <p>输入家电售后问题，Agent 会返回答案、意图和引用来源。</p>
        </div>
        <div class="badge">本地演示版</div>
      </header>
      <div id="messages">
        <div class="msg bot">你好，我是 Aqualink 售后 Agent。可以问我洗衣机故障码、使用维护、保修收费和排障问题。</div>
      </div>
      <form id="chat-form">
        <input id="message" autocomplete="off" placeholder="例如：X100 显示 E2 不排水怎么办？" />
        <button id="send" type="submit">发送</button>
      </form>
    </section>
  </main>
  <script>
    const sessionId = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    const messages = document.querySelector("#messages");
    const form = document.querySelector("#chat-form");
    const input = document.querySelector("#message");
    const send = document.querySelector("#send");

    function addMessage(text, cls, meta = "") {
      const node = document.createElement("div");
      node.className = `msg ${cls}`;
      node.textContent = text;
      if (meta) {
        const small = document.createElement("div");
        small.className = "meta";
        small.textContent = meta;
        node.appendChild(small);
      }
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    async function submitMessage(text) {
      const message = text.trim();
      if (!message) return;
      addMessage(message, "user");
      input.value = "";
      send.disabled = true;
      try {
        const response = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, message })
        });
        const data = await response.json();
        const meta = `intent: ${data.intent || "-"} · citations: ${(data.citations || []).join(", ") || "-"}`;
        addMessage(data.answer || "没有返回内容", "bot", meta);
      } catch (error) {
        addMessage(`请求失败：${error}`, "bot");
      } finally {
        send.disabled = false;
        input.focus();
      }
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitMessage(input.value);
    });
    document.querySelectorAll("[data-q]").forEach((button) => {
      button.addEventListener("click", () => submitMessage(button.dataset.q));
    });
  </script>
</body>
</html>"""


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    project_root = Path(__file__).resolve().parents[3]
    resolved_data_dir = Path(data_dir) if data_dir else project_root / "原始数据"
    agent = ApplianceAgent.from_data_dir(resolved_data_dir)
    app = FastAPI(title="Aqualink 家电售后智能客服 Agent", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(request: ChatRequest) -> dict[str, Any]:
        response = agent.chat(request.session_id, request.message)
        return {
            "answer": response.answer,
            "intent": response.intent,
            "contexts": response.contexts,
            "citations": response.citations,
            "metadata": response.metadata,
        }

    @app.post("/search")
    def search(request: SearchRequest) -> dict[str, Any]:
        results = agent.retriever.hybrid_search(
            request.query,
            model=request.model,
            fault_code=request.fault_code,
            source_types=request.source_types,
            top_k=request.top_k,
        )
        return {
            "results": [
                {
                    "doc_id": result.doc_id,
                    "score": result.score,
                    "text": result.text,
                    "metadata": result.metadata,
                }
                for result in results
            ]
        }

    return app


app = create_app()

# Aqualink 家电售后智能客服 Agent

一个面向虚构家电品牌 **Aqualink** 的售后智能客服项目，覆盖洗衣机使用问答、故障码解释、多轮排障、保修/收费政策说明和安全护栏。

## 功能

- 基于 `原始数据/` 构建可评估的知识块，保留 `doc_id`、型号、故障码、来源类型等元数据。
- 提供混合检索：语义相似度 + 关键词精确匹配 + RRF 融合，适配 `E2`、`X100` 这类短代码。
- 内置安全护栏：拒绝拆机、短接门锁、强电检测等危险请求；识别漏水、跳闸、焦味等高风险信号。
- 支持多轮排障状态机：按 `troubleshooting_flow_tree.yaml` 动态追问。
- 提供 FastAPI 接口和 CLI 演示入口。
- 提供检索评估钩子，可从 FAQ 和历史工单生成 golden set。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m pytest
```

启动 API：

```bash
uvicorn appliance_agent.api.app:app --app-dir src --reload
```

调用示例：

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"demo\",\"message\":\"X100 显示 E2 不排水怎么办？\"}"
```

CLI 演示：

```bash
python scripts/chat_cli.py
```

## 环境变量

`.env` 不会提交到 GitHub。公开模板见 `.env.example`：

- `DASHSCOPE_API_KEY`：百炼 / DashScope API Key
- `QWEN_EMBEDDING_MODEL=text-embedding-v4`
- `QWEN_RERANK_MODEL=qwen3-rerank`
- `DEEPSEEK_API_KEY`：DeepSeek API Key
- `DEEPSEEK_MODEL=deepseek-v4-flash`

当前代码默认离线可运行；云端模型配置用于后续替换检索重排和生成节点。

## API

### `GET /health`

返回服务状态。

### `POST /chat`

请求：

```json
{
  "session_id": "demo",
  "message": "X200 买了两年，排水泵坏了，保修收费吗？"
}
```

响应包含：

- `answer`：客服回复
- `intent`：`diagnose` / `warranty_fee` / `qa` / `safety` / `chitchat`
- `contexts`：使用的上下文文本
- `citations`：引用的 `doc_id`
- `metadata`：型号、故障码、风险等结构化信息

### `POST /search`

旁路检索接口，用于评估或调试。

## 评估

生成 golden set：

```bash
python evaluation/build_golden.py
```

运行检索评估：

```bash
python evaluation/retrieval_eval.py
```

## 项目结构

```text
src/appliance_agent/
  ingestion.py      # 数据加载、差异化分块、元数据
  retrieval.py      # 混合检索和工具化搜索
  guardrail.py      # 安全前置护栏
  flow_engine.py    # YAML 驱动排障状态机
  agent.py          # 会话编排和回复生成
  api/app.py        # FastAPI 服务
evaluation/         # golden set 和检索评估脚本
tests/              # 核心行为测试
configs/            # 默认模型与检索参数
```

## 说明

`docs/` 中的技术设计文档和实现规格说明按要求保留在本地，不随正式项目提交到 GitHub。

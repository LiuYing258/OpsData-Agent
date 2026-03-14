# 🤖 OpsData-Agent 

基于 LangGraph 构建的多模态本地智能体（AI Agent），专注于运维巡检、数据库分析及轻量级本地知识库检索（RAG）。

## 🌟 核心特性
* **多步推理状态机：** 基于 LangGraph 的 ReAct 架构，具备任务拆解与异常报错自我纠错（Self-Correction）能力。
* **极高的安全性：** 软硬双重拦截，防范大模型“工具幻觉（Over-tooling）”与危险系统命令。
* **本地 RAG 检索：** 接入 FAISS 向量库，实现内部运维手册的精准问答。
* **UI 状态解耦：** 采用 Streamlit 构建，通过滑动窗口与工具日志丢弃机制，节省 80% Token 消耗。

## 🚀 快速启动
1. `pip install -r requirements.txt`
2. 复制 `.env.example` 为 `.env` 并填入 API Key。
3. 运行 `streamlit run main.py`

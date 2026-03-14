# 文件名：web_ui.py
import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
# 导入之前的工具
from tools import execute_system_command, query_database, generate_bar_chart, remember_information
# 导入刚刚写好的 RAG 工具
from rag.vector_store import query_knowledge_base
# 确保在顶部引入 SystemMessage
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from tools import execute_system_command, query_database, generate_bar_chart, remember_information
# 导入工具
from tools import execute_system_command, query_database, generate_bar_chart

# ==========================================
# 1. 页面基础配置
# ==========================================
st.set_page_config(page_title="OpsData Agent 控制台", page_icon="🤖", layout="wide")
st.title("🤖 OpsData Agent - 智能运维与数据分析")
st.markdown("通过自然语言下达指令，Agent 会自动拆解任务、调用工具并可视化结果。")

# ==========================================
# 2. 初始化核心引擎 (利用缓存机制提升性能)
# ==========================================
load_dotenv()

# [面试亮点：@st.cache_resource]
# Streamlit 每次交互都会从头运行代码。使用缓存可以确保大模型和 Agent 只被初始化一次，避免重复消耗资源。
@st.cache_resource 
def init_agent():
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0.1
    )
    
   # 找到 init_agent() 函数，将 query_knowledge_base 补充进去
    tools = [execute_system_command, query_database, generate_bar_chart, remember_information, query_knowledge_base]
       
    return create_react_agent(llm, tools)
    # 【修复点】：去掉那个惹祸的 state_modifier，只保留最基础的传入
    return create_react_agent(llm, tools)
agent_executor = init_agent()

# ==========================================
# 3. 记忆管理 (Session State)
# ==========================================
# [面试亮点：状态保持]
# 解决了网页刷新就会“失忆”的问题，将历史对话存在 session_state 中
if "messages" not in st.session_state:
    st.session_state.messages = []

# 在页面上渲染过去的历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. 核心交互流
# ==========================================
# 这是一个漂亮的底部聊天输入框
if prompt := st.chat_input("请输入指令，例如：查一下 mock_data.db 里 ERROR 日志的数量并画图"):
    
    # 1. 将用户的输入存入记忆并显示在界面上
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# 2. 准备历史消息喂给 LangGraph
    # ================= [新增逻辑：读取长时记忆] =================
    memory_context = "暂无。"
    if os.path.exists("memory.md"):
        with open("memory.md", "r", encoding="utf-8") as f:
            memory_context = f.read()
    

    # ================= [优化提示词：注入记忆 + 行为约束] =================
    system_prompt = f"""你是一个顶级的全栈系统运维与数据分析专家。
你可以执行系统命令、查询数据库、并将数据可视化。

【核心行为约束 - 极其重要】：
尽量用简短的语言回答问题，不要长篇大论。

【你的长期记忆】（以下是你必须遵守的设定和历史信息）：
{memory_context}
"""
    
    langchain_messages = [SystemMessage(content=system_prompt)]
    
    # 将之前的短时记忆组装进去
    for m in st.session_state.messages:
        if m["role"] == "user":
            langchain_messages.append(HumanMessage(content=m["content"]))
        else:
            langchain_messages.append(AIMessage(content=m["content"]))
    # 3. Agent 开始工作！
    with st.chat_message("assistant"):
        # [面试亮点：过程折叠面板]
        # 把枯燥的 JSON 参数和 Shell 报错折叠起来，保持界面清爽，懂行的人点开又能看到底层逻辑
        with st.status("🧠 Agent 正在思考与执行...", expanded=True) as status:
            final_response = ""
            
            # 流式读取 Agent 的执行步骤
            for chunk in agent_executor.stream({"messages": langchain_messages}):
                for node_name, node_info in chunk.items():
                    for msg in node_info["messages"]:
                        # 如果是工具调用过程，打印在折叠面板里
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                st.write(f"🔧 **决定调用工具**: `{tool_call['name']}`")
                                st.code(f"参数: {tool_call['args']}", language="json")
                        # 如果是最终的自然语言回复，保存下来
                        elif msg.content:
                            final_response = msg.content
            
            # 任务完成，收起折叠面板
            status.update(label="✅ 任务流转完毕", state="complete", expanded=False)
        langchain_messages = [SystemMessage(content=system_prompt)]
    
    # ================= [新增核心：滑动窗口截断机制] =================
    # 设定只保留最近 5 轮对话（一问一答算两边，所以是 10 条记录）
    MAX_HISTORY = 10 
    
    # 截取最新的记录，丢弃更早的金鱼记忆
    recent_messages = st.session_state.messages[-MAX_HISTORY:] if len(st.session_state.messages) > MAX_HISTORY else st.session_state.messages

    # 将截断后的历史消息组装进去
    for m in recent_messages:
        if m["role"] == "user":
            langchain_messages.append(HumanMessage(content=m["content"]))
        else:
            langchain_messages.append(AIMessage(content=m["content"]))
        # 4. 在界面上打印最终回答
        st.markdown(final_response)
        
        # 5. 智能图片渲染：如果大模型生成了图片，我们直接在网页里展示出来！
        if "log_distribution.png" in final_response or os.path.exists("log_distribution.png"):
             # 使用 try-except 防止文件读取时的意外报错
             try:
                 st.image("log_distribution.png", caption="📊 Agent 自动生成的可视化图表")
             except:
                 pass

        # 6. 将最终回答存入记忆
        st.session_state.messages.append({"role": "assistant", "content": final_response})
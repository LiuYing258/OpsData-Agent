import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import langchain
from tools import execute_system_command, query_database, generate_bar_chart, remember_information
from memory_manager import MemoryManager

# 针对 RAG 模块
try:
    from rag.vector_store import query_knowledge_base
except ImportError:
    query_knowledge_base = None

langchain.debug = True
load_dotenv()

# 1. 初始化核心组件

st.set_page_config(page_title="OpsData Agent", page_icon="🤖", layout="wide")
memory_manager = MemoryManager()

@st.cache_resource 
def init_agent_core():
    """初始化大模型与 LangGraph 状态机"""
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0.1,
        model_kwargs={"frequency_penalty": 0.5, "presence_penalty": 0.1},
        max_tokens=1000
    )
    tools = [execute_system_command, query_database, generate_bar_chart, remember_information]
    if query_knowledge_base:
         tools.append(query_knowledge_base)
         
    return create_react_agent(llm, tools)

agent_executor = init_agent_core()

# ==========================================
# 2. UI 界面与状态管理
# ==========================================
st.title("🤖 OpsData Agent - 智能本地数据运维助手")

if "messages" not in st.session_state:
    st.session_state.messages = []

# 渲染历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# 3. 核心交互逻辑

if prompt := st.chat_input("请输入指令，例如：查一下db类文件里 ERROR 日志的数量并画图"):
    
    # 用户输入上屏
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 组装系统级 Prompt (加载长期记忆)
    system_prompt = f"""你是一个顶级的全栈系统运维与数据分析专家。

【核心行为约束 - 极其重要】：
1. 基础对话（打招呼、闲聊、常识数学题等），必须直接用自然语言回答，绝对禁止调用任何工具！
2. 只有需要获取系统状态、数据库数据或内部规范时，才允许调用对应工具。
3. 尽量用简短专业的语言回答。


【长期记忆/全局规范】（以下信息具有最高执行优先级）：
{memory_manager.get_long_term_memory()}
"""
    
    # 处理短期记忆 (防 Token 爆炸)
    recent_messages = memory_manager.get_short_term_memory(st.session_state.messages)

    # 组装发给大模型的最终上下文
    langchain_messages = [SystemMessage(content=system_prompt)]
    for m in recent_messages:
        role_class = HumanMessage if m["role"] == "user" else AIMessage
        langchain_messages.append(role_class(content=m["content"]))

    # 唤醒 Agent 引擎
    with st.chat_message("assistant"):
        with st.status("Agent 正在深度思考与执行操作...", expanded=True) as status:
            final_response = ""
            
            # 开启状态机流转 (加入防死循环保险)
            for chunk in agent_executor.stream({"messages": langchain_messages}, config={"recursion_limit": 50}):
                for node_name, node_info in chunk.items():
                    if "messages" in node_info:
                        for msg in node_info["messages"]:
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    st.write(f"🔧 **调用组件**: `{tool_call['name']}`")
                                    st.code(f"入参: {tool_call['args']}", language="json")
                            elif msg.content:
                                final_response = msg.content
            
            status.update(label="✅ 任务闭环完成", state="complete", expanded=False)
        
        # 渲染最终文本
        st.markdown(final_response)
        
        # 渲染图表附件
        chart_path = "log_distribution.png"
        if os.path.exists(chart_path) and ("图" in final_response or "chart" in final_response):
             try:
                 st.image(chart_path, caption="系统自动生成的数据可视化图表")
                 os.remove(chart_path) # 阅后即焚，保持环境整洁
             except Exception as e:
                 st.error(f"图表加载失败: {e}")

        # 写入短期记忆
        st.session_state.messages.append({"role": "assistant", "content": final_response})
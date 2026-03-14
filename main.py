import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import execute_system_command, query_database, generate_bar_chart, remember_information
from rag.vector_store import query_knowledge_base
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import langchain

#LangChain 底层调试日志，出问题的时候可以进行调试
langchain.debug = True

st.set_page_config(page_title="OpsData Agent 控制台", page_icon="🤖", layout="wide")
st.title("🤖 OpsData Agent - 智能运维与数据分析")
st.markdown("通过自然语言下达指令，Agent 会自动拆解任务、调用工具并可视化结果。")

load_dotenv()

@st.cache_resource 
def init_agent():
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://api.deepseek.com/v1",
        temperature=0.1,
        model_kwargs={
            "frequency_penalty": 0.5,
            "presence_penalty": 0.1
        },
        max_tokens=1000
    )
   
    tools = [execute_system_command, query_database, generate_bar_chart, remember_information, query_knowledge_base]
    return create_react_agent(llm, tools)

agent_executor = init_agent()

# 短时记忆管理 (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 在页面上渲染过去的历史对话
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入指令，例如：查一下 mock_data.db 里 ERROR 日志的数量并画图"):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 防御性读取长时记忆memory.md
    memory_context = "暂无。"
    if os.path.exists("memory.md"):
        with open("memory.md", "r", encoding="utf-8") as f:
            memory_context = f.read()

    # 3. System Prompt (融入长时记忆与强约束)
    system_prompt = f"""你是一个顶级的全栈系统运维与数据分析专家。
你可以执行系统命令、查询数据库、并将数据可视化。

【核心行为约束 - 极其重要】：
1. 如果用户问的是基础数学题（如1+1）、打招呼或常识聊天这类不关乎数据库和文件的问题，请直接用自然语言回答，绝对不要调用任何工具！
2. 只有在需要获取系统真实状态、数据库数据或内部规范时，才允许调用工具，禁止多次反复输出相同内容。
3. 尽量用简短的语言回答问题，不要长篇大论。

【你的长期记忆】（以下是你必须遵守的设定和历史信息）：
{memory_context}
"""
    
    # 滑动窗口截断机制 (组装消息前，先过滤历史记录，保护 Token)
    MAX_HISTORY = 10 
    recent_messages = st.session_state.messages[-MAX_HISTORY:] if len(st.session_state.messages) > MAX_HISTORY else st.session_state.messages

    # 组装发给大模型的消息列表 
    langchain_messages = [SystemMessage(content=system_prompt)]
    for m in recent_messages:
        if m["role"] == "user":
            langchain_messages.append(HumanMessage(content=m["content"]))
        else:
            langchain_messages.append(AIMessage(content=m["content"]))

    # 唤醒 Agent 执行任务
    with st.chat_message("assistant"):
        with st.status("Agent 正在思考与执行...", expanded=True) as status:
            final_response = ""
            
            # 流式读取 Agent 的执行步骤，加上 50 次防死循环，方便调试
            for chunk in agent_executor.stream(
                {"messages": langchain_messages},
                config={"recursion_limit": 50}  
            ):
                print("\n[当前状态机 Chunk] ====>", chunk, flush=True)
                for node_name, node_info in chunk.items():
                    if "messages" in node_info:
                        for msg in node_info["messages"]:
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tool_call in msg.tool_calls:
                                    st.write(f"🔧 **决定调用工具**: `{tool_call['name']}`")
                                    st.code(f"参数: {tool_call['args']}", language="json")
                            elif msg.content:
                                final_response = msg.content
            
            status.update(label="任务流转完毕", state="complete", expanded=False)
        
   
        st.markdown(final_response)
        
        # 如果回答提到了画图，或者本地生成了图片，则渲染出来
        if "log_distribution.png" in final_response or os.path.exists("log_distribution.png"):
             try:
                 st.image("log_distribution.png", caption="Agent 自动生成的可视化图表")
               
                 os.remove("log_distribution.png") 
             except:
                 pass

        # 将最终回答存入 Session State 记忆
        st.session_state.messages.append({"role": "assistant", "content": final_response})
# 文件名：main.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# 1. 导入终极三剑客！
from tools import execute_system_command, query_database, generate_bar_chart

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat", 
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0 
)

# 2. 装备全部三个工具
tools = [execute_system_command, query_database, generate_bar_chart]

agent_executor = create_react_agent(llm, tools)

# 3. 下达“终极连环任务”
user_task = """
请帮我完成以下系列任务：
1. 检查当前目录下是否有 mock_data.db 文件。
2. 如果有，请查询 server_logs 表，统计所有级别的日志分布情况（例如 INFO, WARNING, ERROR 各有多少条）。
3. 将统计好的分布数据，画成一张柱状图，标题为“系统日志级别分布图”，文件保存为 'log_distribution.png'。
最后请告诉我任务的执行结果。
"""

messages = [
    ("system", "你是一个顶级的全栈系统运维与数据分析专家。你可以执行系统命令、查询数据库、并将数据可视化。如果报错，请自主尝试修正。"),
    ("human", user_task)
]

print("=== OpsData-Agent 终极试炼开始 ===")

for chunk in agent_executor.stream({"messages": messages}):
    for node_name, node_info in chunk.items():
        print(f"\n---> [当前节点: {node_name}]")
        for msg in node_info["messages"]:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"🧠 大脑决定调用工具: {tool_call['name']}, 参数: {tool_call['args']}")
            elif msg.content:
                print(msg.content)

print("\n=== 任务流转完毕 ===")
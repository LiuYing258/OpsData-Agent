# tools.py
import subprocess
import sqlite3
import matplotlib.pyplot as plt
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from memory_manager import MemoryManager

# 初始化记忆管理器实例，供工具调用
memory_manager = MemoryManager()

# 工具 ：系统命令执行

class SystemCommandSchema(BaseModel):
    command: str = Field(description="需要执行的合法 Windows/Linux 命令行字符串")

@tool(args_schema=SystemCommandSchema)
def execute_system_command(command: str) -> str:
    """
    【高权限工具】执行操作系统的命令行指令。
    用于查看系统信息、文件列表、网络状态或执行底层运维操作。
    """
    forbidden_words = ["rm", "del", "format", "shutdown", "reboot", "diskpart"]
    cmd_lower = command.lower()
    
    for word in forbidden_words:
        if f" {word} " in f" {cmd_lower} " or cmd_lower.startswith(f"{word} "):
            return f"❌ 安全拦截：命令包含高危操作 '{word}'，已被系统拒绝。"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="ignore" 
        )
        return f"✅ 执行成功:\n{result.stdout}" if result.returncode == 0 else f"⚠️ 执行失败:\n{result.stderr}\n请分析报错并尝试修正。"
    except subprocess.TimeoutExpired:
        return "⏳ 执行超时：命令耗时过长被中止。"
    except Exception as e:
        return f"❌ 未知异常：{str(e)}"


# 工具 ：数据库查询

class DBQuerySchema(BaseModel):
    sql_query: str = Field(description="合法的 SQLite 查询语句，必须是 SELECT 操作")

@tool(args_schema=DBQuerySchema)
def query_database(sql_query: str) -> str:
    """执行 SQL 查询语句，获取数据库中的业务数据或日志记录。"""
    db_path = "mock_data.db" 
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if not sql_query.strip().upper().startswith("SELECT"):
            return "❌ 安全拦截：只允许执行 SELECT 查询操作。"
            
        cursor.execute(sql_query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        if not results:
            return "⚠️ 查询成功，但没有匹配的数据。请检查表名或 WHERE 条件。"
            
        output = f"列名: {column_names}\n"
        for row in results[:50]: 
            output += f"{row}\n"
        return f"✅ 查询成功 (最多显示前50条):\n{output}"
        
    except sqlite3.OperationalError as e:
        return f"❌ SQL 报错: {str(e)}\n请先用 'SELECT name FROM sqlite_master WHERE type=\"table\";' 查表结构。"
    except Exception as e:
        return f"❌ 数据库未知报错: {str(e)}"


# 工具 ：数据可视化 (告别 JSON 解析噩梦)

class BarChartSchema(BaseModel):
    categories: list[str] = Field(description="柱状图的 X 轴类别列表，例如 ['INFO', 'ERROR']")
    values: list[float] = Field(description="柱状图的 Y 轴数值列表，例如 [59.0, 15.0]")
    title: str = Field(description="图表的标题")

@tool(args_schema=BarChartSchema)
def generate_bar_chart(categories: list[str], values: list[float], title: str) -> str:
    """
    【数据分析工具】根据提供的数据生成柱状图并保存为图片。
    绝对规则：只有当用户的原始输入中明确包含“画图”、“可视化”、“图表”等明确指令时，才允许调用此工具！
    """
    save_path = "log_distribution.png"
    try:
        if len(categories) != len(values):
            return "❌ 绘图失败：X轴类别与Y轴数值的长度不匹配。"
            
        plt.rcParams['font.sans-serif'] = ['SimHei'] 
        plt.rcParams['axes.unicode_minus'] = False  
        
        plt.figure(figsize=(8, 6))
        colors = ['#4CAF50', '#FF9800', '#F44336', '#2196F3', '#9C27B0']
        bars = plt.bar(categories, values, color=colors[:len(categories)])
        
        plt.title(title, fontsize=16)
        plt.xlabel("类别", fontsize=12)
        plt.ylabel("数值", fontsize=12)
        
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, int(yval), ha='center', va='bottom')
            
        plt.savefig(save_path, dpi=300)
        plt.close() 
        return f"✅ 图表已成功生成，文件已保存至：{save_path}"
    except Exception as e:
        return f"❌ 绘图时发生错误: {str(e)}"


# 工具 ：长时记忆写入

class RememberSchema(BaseModel):
    info: str = Field(description="需要永久记住的核心要点，语言需精简")

@tool(args_schema=RememberSchema)
def remember_information(info: str) -> str:
    """永久记住用户的偏好、系统配置或重要规则。"""
    return memory_manager.save_to_long_term_memory(info)
import subprocess
from langchain_core.tools import tool
import sqlite3
@tool
def execute_system_command(command: str) -> str:
    """
    执行操作系统的命令行指令。
    当你需要查看系统信息、文件列表、网络状态或执行底层运维操作时，必须调用此工具。
    输入参数 command 应该是合法的命令行字符串。
    """
    forbidden_words = ["rm", "del", "format", "shutdown", "reboot", "diskpart"]
    cmd_lower = command.lower()
    
    for word in forbidden_words:
        if f" {word} " in f" {cmd_lower} " or cmd_lower.startswith(f"{word} "):
            return f"❌ 安全拦截：命令包含高危操作 '{word}'，已被系统拒绝。"

    try:
        print(f"\n[🔧 工具执行中] 正在运行: {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8", 
            errors="ignore" 
        )
        if result.returncode == 0:
            return f"✅ 执行成功:\n{result.stdout}"
        else:
            return f"⚠️ 执行失败:\n{result.stderr}\n请分析报错并尝试新命令。"
    except subprocess.TimeoutExpired:
        return "⏳ 执行超时：命令耗时过长被中止。"
    except Exception as e:
        return f"❌ 未知异常：{str(e)}"
    
# 第二个工具：数据库查询引擎

@tool
def query_database(sql_query: str) -> str:
    """
    执行 SQL 查询语句。
    当你需要查询数据库中的业务数据、日志记录或任何表格数据时，调用此工具。
    输入参数 sql_query 必须是一条合法的 SQLite 查询语句。
    """
    # 模拟数据库文件将放在当前目录下
    db_path = "mock_data.db" 
    
    try:
        print(f"\n[🗄️ 数据库查询中] 执行 SQL: {sql_query}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # 拦截非查询操作
        if not sql_query.strip().upper().startswith("SELECT"):
            conn.commit()
            conn.close()
            return "✅ 数据修改语句已执行。"
            
        # 获取查询结果
        results = cursor.fetchall()
        column_names = [description[0] for description in cursor.description] if cursor.description else []
        conn.close()
        
        if not results:
            return "⚠️ 查询成功，但没有匹配的数据。请检查表名或 WHERE 条件。"
            
        
        # 限制只返回前 50 条数据
        output = f"列名: {column_names}\n"
        for row in results[:50]: 
            output += f"{row}\n"
            
        return f"✅ 查询成功 (为防止内存溢出，最多显示前50条):\n{output}"
        
    except sqlite3.OperationalError as e:
     
        # 当表不存在或字段写错时，告诉大模型去查系统表，而不是让程序崩溃。
        return f"❌ SQL 执行报错:\n{str(e)}\n请先使用 'SELECT name FROM sqlite_master WHERE type=\"table\";' 查询当前数据库中有哪些表，然后再重新生成正确的 SQL 语句。"
    except Exception as e:
        return f"❌ 数据库未知报错: {str(e)}"
    
import json
import matplotlib.pyplot as plt


# 第三个工具：数据可视化

@tool
def generate_bar_chart(data_json: str, title: str, save_path: str = "chart.png") -> str:
    """
    【危险警告：高权限工具】
    作用：根据提供的数据生成柱状图并保存为图片。
    调用条件（必须绝对遵守）：只有当用户的原始输入中明确包含“画图”、“可视化”、“图表”、“柱状图”等明确指令时，才允许调用此工具！
    如果用户只是让你“统计”、“查询”、“计算”数量，绝对禁止调用此工具！违规调用将导致系统崩溃！
    输入参数 data_json 必须是一个严格合法的 JSON 字符串，包含 'categories' (字符串列表) 和 'values' (数字列表)。
    例如: '{"categories": ["INFO", "WARNING", "ERROR"], "values": [59, 26, 15]}'
    """
    try:
        print(f"\n[📊 绘图工具执行中] 正在生成图表: {title}")
        
       
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体为黑体
        plt.rcParams['axes.unicode_minus'] = False    # 解决保存图像是负号'-'显示为方块的问题
        
        # 解析大模型传过来的 JSON 数据
        data = json.loads(data_json)
        categories = data.get("categories", [])
        values = data.get("values", [])
        
        if not categories or not values or len(categories) != len(values):
            return " 绘图失败：数据格式不正确或类别与数值的长度不匹配，请检查传入的 JSON 结构。"
            
      
        plt.figure(figsize=(8, 6))
        colors = ['#4CAF50', '#FF9800', '#F44336', '#2196F3', '#9C27B0']
        bars = plt.bar(categories, values, color=colors[:len(categories)])
        
        plt.title(title, fontsize=16)
        plt.xlabel("日志级别", fontsize=12)
        plt.ylabel("出现次数", fontsize=12)
        
        # 在每个柱子顶部写上具体的数字
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, int(yval), ha='center', va='bottom')
            
        # 保存图片
        plt.savefig(save_path, dpi=300)
        plt.close() # 释放内存，防止连续绘图导致 OOM
        
        return f"图表已成功生成，文件已保存至当前目录：{save_path}"
        
    except json.JSONDecodeError as e:
  
        return f"❌ JSON 解析失败: {str(e)}。请确保你传入的是标准的 JSON 字符串，不要带 markdown 代码块标记。"
    except Exception as e:
        return f"❌ 绘图时发生未知错误: {str(e)}"
    


# 第四个工具：长时记忆写入

@tool
def remember_information(info: str) -> str:
    """
    当你需要永久记住用户的偏好、系统密码、特定路径或重要规则时，必须调用此工具。
    输入参数 info 是你需要记住的具体内容，请尽量精简并提取核心要点。
    """
    try:
        print(f"\n[记忆写入中] 正在保存: {info}")
        # 以追加模式 (a) 打开文件，如果不存在会自动创建
        with open("memory.md", "a", encoding="utf-8") as f:
            f.write(f"- {info}\n")
        return "记忆已成功永久保存到 memory.md 中。"
    except Exception as e:
        return f"❌ 保存记忆失败: {str(e)}"
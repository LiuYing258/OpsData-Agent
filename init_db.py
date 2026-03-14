# 文件名：init_db.py
import sqlite3
import random
from datetime import datetime, timedelta

print("正在初始化模拟数据库 mock_data.db ...")
conn = sqlite3.connect("mock_data.db")
cursor = conn.cursor()

# 创建一张系统日志表
cursor.execute("""
CREATE TABLE IF NOT EXISTS server_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date TEXT,
    level TEXT,
    message TEXT
)
""")
cursor.execute("DELETE FROM server_logs") # 清空旧数据

# 插入 100 条假日志数据 (包含 ERROR 和 INFO)
base_date = datetime.now()
for i in range(100):
    log_date = (base_date - timedelta(hours=random.randint(1, 72))).strftime("%Y-%m-%d %H:%M:%S")
    level = random.choice(["INFO", "INFO", "INFO", "ERROR", "WARNING"])
    message = "Connection timeout" if level == "ERROR" else "Service running normally"
    cursor.execute("INSERT INTO server_logs (log_date, level, message) VALUES (?, ?, ?)", (log_date, level, message))

conn.commit()
conn.close()
print("✅ 初始化完成！生成了包含 100 条数据的 server_logs 表。")
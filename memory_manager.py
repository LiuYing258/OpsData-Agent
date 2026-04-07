# memory_manager.py
import os
from typing import List, Dict

class MemoryManager:
    """
    Agent 记忆管理中心 (统一管理长/短时记忆)
    """
    def __init__(self, ltm_path: str = "memory.md", max_stm_history: int = 10):
        self.ltm_path = ltm_path
        self.max_stm_history = max_stm_history

    def get_long_term_memory(self) -> str:
        """读取长期记忆 (LTM)"""
        if os.path.exists(self.ltm_path):
            with open(self.ltm_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else "暂无长期记忆。"
        return "暂无长期记忆。"

    def save_to_long_term_memory(self, info: str) -> str:
        """写入长期记忆 (LTM)"""
        try:
            with open(self.ltm_path, "a", encoding="utf-8") as f:
                f.write(f"- {info}\n")
            return "✅ 记忆已成功永久保存。"
        except Exception as e:
            return f"❌ 保存记忆失败: {str(e)}"

    def get_short_term_memory(self, session_messages: List[Dict]) -> List[Dict]:
        """
        读取并截断短期记忆 (STM)
        采用滑动窗口机制，保护 Token 上限
        """
        if len(session_messages) > self.max_stm_history:
            return session_messages[-self.max_stm_history:]
        return session_messages
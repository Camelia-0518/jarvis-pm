"""
上下文优化器

提供上下文压缩、长期记忆管理、多轮对话优化等功能
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta




class Message(BaseModel):
    """对话消息"""
    role: str = Field(description="角色: user/assistant/system")
    content: str = Field(description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    """对话上下文"""
    session_id: str = Field(description="会话ID")
    messages: List[Message] = Field(default_factory=list)
    summary: str = Field(default="", description="对话摘要")
    key_points: List[str] = Field(default_factory=list, description="关键点")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="用户偏好")

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """添加消息"""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata or {}
        ))

    def get_recent_messages(self, n: int = 5) -> List[Message]:
        """获取最近的n条消息"""
        return self.messages[-n:] if n < len(self.messages) else self.messages


class ContextOptimizer:
    """上下文优化器"""

    def __init__(self, max_context_length: int = 4000):
        self.max_context_length = max_context_length
        self.conversations: Dict[str, ConversationContext] = {}
        self.long_term_memory: Dict[str, Any] = {}

    def optimize_context(
        self,
        session_id: str,
        current_query: str,
        retrieved_docs: Optional[List[str]] = None
    ) -> str:
        """
        优化上下文

        Args:
            session_id: 会话ID
            current_query: 当前查询
            retrieved_docs: 检索到的文档

        Returns:
            优化后的上下文
        """
        # 获取或创建对话上下文
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationContext(session_id=session_id)

        context = self.conversations[session_id]

        # 构建优化后的上下文
        parts = []

        # 1. 系统提示
        parts.append(self._get_system_prompt())

        # 2. 长期记忆（关键信息）
        memory = self._get_relevant_memory(session_id, current_query)
        if memory:
            parts.append(f"【历史记忆】\n{memory}\n")

        # 3. 检索文档
        if retrieved_docs:
            docs_context = self._format_retrieved_docs(retrieved_docs)
            parts.append(docs_context)

        # 4. 近期对话历史
        recent_history = self._get_compressed_history(context)
        if recent_history:
            parts.append(f"【近期对话】\n{recent_history}\n")

        # 5. 当前查询
        parts.append(f"【当前需求】\n{current_query}")

        # 合并并截断
        full_context = "\n".join(parts)
        return self._truncate_if_needed(full_context)

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        return """【系统提示】
你是一位资深医疗信息化产品经理助手，专注于：
1. 协助前端开发背景的产品经理完成产品设计
2. 医疗信息化行业需求分析
3. PRD文档生成和优化

工作原则：
- 聚焦产品价值，避免过早讨论技术实现
- 医疗场景自动触发合规检查
- 多院区功能主动提示政策差异

"""

    def _get_relevant_memory(self, session_id: str, query: str) -> str:
        """获取相关记忆"""
        memory_parts = []

        # 用户偏好
        if session_id in self.long_term_memory:
            prefs = self.long_term_memory[session_id].get("preferences", {})
            if prefs.get("industry") == "medical":
                memory_parts.append("- 行业：医疗信息化")
            if prefs.get("focus"):
                memory_parts.append(f"- 关注重点：{prefs['focus']}")

        # 项目上下文
        if session_id in self.conversations:
            context = self.conversations[session_id]
            if context.key_points:
                memory_parts.append("- 已确认的关键点：")
                for point in context.key_points[-3:]:
                    memory_parts.append(f"  • {point}")

        return "\n".join(memory_parts) if memory_parts else ""

    def _format_retrieved_docs(self, docs: List[str]) -> str:
        """格式化检索文档"""
        if not docs:
            return ""

        formatted = ["【参考资料】"]
        for i, doc in enumerate(docs[:3], 1):
            formatted.append(f"[{i}] {doc[:500]}...")  # 截断

        return "\n".join(formatted) + "\n"

    def _get_compressed_history(self, context: ConversationContext) -> str:
        """获取压缩后的对话历史"""
        recent = context.get_recent_messages(3)

        if not recent:
            return ""

        # 提取关键信息，压缩对话
        compressed = []
        for msg in recent:
            prefix = "用户" if msg.role == "user" else "助手"
            # 截断长消息
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            compressed.append(f"{prefix}：{content}")

        return "\n".join(compressed)

    def _truncate_if_needed(self, context: str) -> str:
        """如果需要则截断"""
        max_chars = self.max_context_length * 4  # 粗略估算

        if len(context) <= max_chars:
            return context

        # 智能截断：保留开头和结尾，中间截断
        half = max_chars // 2 - 100
        return context[:half] + "\n\n... [中间内容省略] ...\n\n" + context[-half:]

    def update_memory(self, session_id: str, key: str, value: Any):
        """更新长期记忆"""
        if session_id not in self.long_term_memory:
            self.long_term_memory[session_id] = {}

        self.long_term_memory[session_id][key] = value

    def add_key_point(self, session_id: str, point: str):
        """添加关键点"""
        if session_id in self.conversations:
            self.conversations[session_id].key_points.append(point)
            # 保持最近10个关键点
            self.conversations[session_id].key_points = \
                self.conversations[session_id].key_points[-10:]

    def clear_old_sessions(self, days: int = 7):
        """清理旧会话"""
        cutoff = datetime.now() - timedelta(days=days)

        expired = []
        for session_id, context in self.conversations.items():
            if context.messages:
                last_message_time = context.messages[-1].timestamp
                if last_message_time < cutoff:
                    expired.append(session_id)

        for session_id in expired:
            del self.conversations[session_id]

    def get_session_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        if session_id not in self.conversations:
            return None

        context = self.conversations[session_id]

        if not context.messages:
            return "新会话"

        # 生成简单摘要
        user_msgs = [m for m in context.messages if m.role == "user"]
        if user_msgs:
            topics = [m.content[:50] for m in user_msgs[-3:]]
            return " | ".join(topics)

        return "进行中"
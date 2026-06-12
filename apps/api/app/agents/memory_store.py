#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长期记忆存储系统

记录用户偏好、项目风格、反馈，新项目自动继承历史偏好
支持基于内容相似度的记忆检索
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'



from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    user_id: str
    memory_type: str  # preference / style / feedback / context
    content: Dict[str, Any]
    tags: List[str]
    project_id: Optional[str]
    importance: float
    access_count: int
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "tags": self.tags,
            "project_id": self.project_id,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MemoryStore:
    """
    长期记忆存储

    管理用户长期记忆，支持：
    - 存储和检索记忆
    - 基于标签和内容的相似度搜索
    - 自动提取项目风格偏好
    - 新项目继承历史偏好
    """

    def __init__(self, db_session=None):
        self._db = db_session
        self._in_memory: Dict[str, List[MemoryItem]] = {}  # user_id -> memories

    async def save(
        self,
        user_id: str,
        memory_type: str,
        content: Dict[str, Any],
        tags: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        importance: float = 5.0,
    ) -> MemoryItem:
        """
        保存记忆

        Args:
            user_id: 用户ID
            memory_type: 记忆类型
            content: 记忆内容
            tags: 标签
            project_id: 关联项目
            importance: 重要性

        Returns:
            MemoryItem: 保存的记忆
        """
        item = MemoryItem(
            id=str(uuid4()),
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            tags=tags or [],
            project_id=project_id,
            importance=importance,
            access_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        if self._db:
            from app.models.memory import MemoryEntry
            entry = MemoryEntry(
                id=item.id,
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                tags=tags or [],
                project_id=project_id,
                importance=importance,
                access_count=0,
            )
            self._db.add(entry)
            await self._db.commit()

        # 同时保存到内存缓存
        if user_id not in self._in_memory:
            self._in_memory[user_id] = []
        self._in_memory[user_id].append(item)

        return item

    async def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryItem]:
        """
        获取用户记忆

        Args:
            user_id: 用户ID
            memory_type: 记忆类型过滤
            tags: 标签过滤（匹配任意一个）
            project_id: 项目过滤
            limit: 返回数量

        Returns:
            记忆列表
        """
        memories = self._in_memory.get(user_id, [])

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        if tags:
            memories = [m for m in memories if any(t in m.tags for t in tags)]

        if project_id:
            memories = [m for m in memories if m.project_id == project_id]

        # 按重要性降序，再按更新时间降序
        memories = sorted(
            memories,
            key=lambda m: (m.importance, m.updated_at.timestamp()),
            reverse=True,
        )

        # 增加访问计数
        for m in memories[:limit]:
            m.access_count += 1

        return memories[:limit]

    async def search_similar(
        self,
        user_id: str,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[tuple[MemoryItem, float]]:
        """
        基于内容相似度搜索记忆

        使用简单的 TF-IDF 风格的关键词重叠度计算

        Args:
            user_id: 用户ID
            query: 查询文本
            memory_type: 记忆类型过滤
            top_k: 返回数量

        Returns:
            [(记忆, 相似度分数)]
        """
        memories = self._in_memory.get(user_id, [])

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        query_words = set(self._tokenize(query))
        if not query_words:
            return []

        scored = []
        for memory in memories:
            memory_text = self._memory_to_text(memory)
            memory_words = set(self._tokenize(memory_text))
            if not memory_words:
                continue

            # Jaccard 相似度
            intersection = len(query_words & memory_words)
            union = len(query_words | memory_words)
            similarity = intersection / union if union > 0 else 0.0

            # 标签匹配加分
            tag_overlap = sum(1 for tag in memory.tags if any(qw in tag or tag in qw for qw in query_words))
            similarity += tag_overlap * 0.1

            # 重要性加权
            similarity *= (0.5 + memory.importance / 10.0)

            if similarity > 0:
                scored.append((memory, round(similarity, 3)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def get_preferences_for_project(
        self,
        user_id: str,
        project_context: str,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        为新项目获取继承的偏好

        基于项目上下文搜索相关历史偏好，合并为项目初始化配置

        Args:
            user_id: 用户ID
            project_context: 项目上下文描述
            industry: 行业类型

        Returns:
            合并后的偏好配置
        """
        # 搜索相关记忆
        similar = await self.search_similar(user_id, project_context, top_k=10)

        preferences: Dict[str, Any] = {
            "industry": industry,
            "style_hints": [],
            "compliance_focus": [],
            "common_patterns": [],
            "avoid_patterns": [],
        }

        for memory, score in similar:
            content = memory.content
            if memory.memory_type == "preference":
                if "style" in content:
                    preferences["style_hints"].append(content["style"])
                if "compliance_focus" in content:
                    preferences["compliance_focus"].extend(content["compliance_focus"])
                if "avoid" in content:
                    preferences["avoid_patterns"].extend(content["avoid"])

            elif memory.memory_type == "style":
                if "description" in content:
                    preferences["style_hints"].append(content["description"])
                if "patterns" in content:
                    preferences["common_patterns"].extend(content["patterns"])

            elif memory.memory_type == "feedback":
                if "suggestions" in content:
                    preferences["style_hints"].extend(content["suggestions"])

        # 去重
        for key in ["style_hints", "compliance_focus", "common_patterns", "avoid_patterns"]:
            preferences[key] = list(dict.fromkeys(preferences[key]))[:10]  # 保留前10个

        return preferences

    async def record_project_style(
        self,
        user_id: str,
        project_id: str,
        style_summary: str,
        tags: Optional[List[str]] = None,
    ) -> MemoryItem:
        """
        记录项目风格

        Args:
            user_id: 用户ID
            project_id: 项目ID
            style_summary: 风格总结
            tags: 标签

        Returns:
            MemoryItem
        """
        return await self.save(
            user_id=user_id,
            memory_type="style",
            content={
                "description": style_summary,
                "project_id": project_id,
            },
            tags=tags or [],
            project_id=project_id,
            importance=7.0,
        )

    async def record_feedback(
        self,
        user_id: str,
        project_id: str,
        feedback: str,
        suggestions: List[str],
    ) -> MemoryItem:
        """
        记录用户反馈

        Args:
            user_id: 用户ID
            project_id: 项目ID
            feedback: 反馈内容
            suggestions: 改进建议

        Returns:
            MemoryItem
        """
        return await self.save(
            user_id=user_id,
            memory_type="feedback",
            content={
                "feedback": feedback,
                "suggestions": suggestions,
                "project_id": project_id,
            },
            tags=["feedback", f"project:{project_id}"],
            project_id=project_id,
            importance=8.0,
        )

    async def record_preference(
        self,
        user_id: str,
        preference_type: str,
        value: Any,
        tags: Optional[List[str]] = None,
    ) -> MemoryItem:
        """
        记录用户偏好

        Args:
            user_id: 用户ID
            preference_type: 偏好类型（style / compliance / format 等）
            value: 偏好值
            tags: 标签

        Returns:
            MemoryItem
        """
        return await self.save(
            user_id=user_id,
            memory_type="preference",
            content={
                "type": preference_type,
                "value": value,
            },
            tags=tags or [preference_type],
            importance=6.0,
        )

    def _tokenize(self, text: str) -> List[str]:
        """简单的文本分词"""
        import re
        text = text.lower()
        # 保留中文和英文单词
        words = re.findall(r'[a-zA-Z]+|[一-鿿]', text)
        return words

    def _memory_to_text(self, memory: MemoryItem) -> str:
        """将记忆转换为可搜索的文本"""
        parts = []
        parts.append(memory.memory_type)
        parts.extend(memory.tags)

        content = memory.content
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            parts.append(item)

        return " ".join(parts)

    async def delete(self, memory_id: str, user_id: str) -> bool:
        """删除记忆"""
        if user_id in self._in_memory:
            original_len = len(self._in_memory[user_id])
            self._in_memory[user_id] = [
                m for m in self._in_memory[user_id] if m.id != memory_id
            ]
            return len(self._in_memory[user_id]) < original_len
        return False

    async def clear_user_memories(self, user_id: str) -> int:
        """清空用户所有记忆"""
        count = len(self._in_memory.get(user_id, []))
        self._in_memory[user_id] = []
        return count
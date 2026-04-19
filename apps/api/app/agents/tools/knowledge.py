#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库查询工具

查询 Obsidian 知识库内容
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
from typing import Dict, Any, List
import re

from .base import BaseTool, ToolParameter, ToolResult, ParameterType


class KnowledgeQueryTool(BaseTool):
    """
    知识库查询工具

    查询 Obsidian 知识库中的相关文档
    """

    name = "search_knowledge"
    description = "查询知识库中的相关文档和信息"
    version = "1.0.0"
    parameters = [
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="查询关键词",
            required=True
        ),
        ToolParameter(
            name="limit",
            type=ParameterType.INTEGER,
            description="返回结果数量",
            required=False,
            default=5
        ),
        ToolParameter(
            name="folder",
            type=ParameterType.STRING,
            description="限定文件夹",
            required=False,
            default=""
        )
    ]

    # 知识库路径
    VAULT_PATH = "C:/Users/13400/Documents/Obsidian/MyVault"

    async def execute(
        self,
        query: str,
        limit: int = 5,
        folder: str = ""
    ) -> ToolResult:
        """
        执行知识库查询

        Args:
            query: 查询关键词
            limit: 返回数量
            folder: 限定文件夹

        Returns:
            ToolResult: 查询结果
        """
        try:
            results = await self._search_vault(query, limit, folder)

            return ToolResult.success_result(
                output=f"找到 {len(results)} 条相关知识",
                data={
                    "query": query,
                    "total": len(results),
                    "results": results
                }
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"查询失败: {str(e)}"
            )

    async def _search_vault(
        self,
        query: str,
        limit: int,
        folder: str
    ) -> List[Dict[str, Any]]:
        """搜索知识库"""
        results = []
        search_path = Path(self.VAULT_PATH)

        if folder:
            search_path = search_path / folder

        if not search_path.exists():
            return results

        # 简单的关键词匹配搜索
        query_lower = query.lower()

        for file_path in search_path.rglob("*.md"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 检查是否匹配
                if query_lower in content.lower():
                    # 提取摘要
                    snippet = self._extract_snippet(content, query)

                    # 计算相关度（简单实现）
                    relevance = content.lower().count(query_lower)

                    # 获取相对路径
                    rel_path = file_path.relative_to(self.VAULT_PATH)

                    results.append({
                        "title": file_path.stem,
                        "path": str(rel_path),
                        "folder": str(rel_path.parent),
                        "snippet": snippet,
                        "relevance": relevance,
                        "obsidian_uri": f"obsidian://open?vault=MyVault&file={rel_path.stem}"
                    })

                    if len(results) >= limit * 3:  # 收集更多用于排序
                        break

            except Exception:
                continue

        # 按相关度排序
        results.sort(key=lambda x: x["relevance"], reverse=True)

        return results[:limit]

    def _extract_snippet(self, content: str, query: str, length: int = 200) -> str:
        """提取包含关键词的文本片段"""
        content_lower = content.lower()
        query_lower = query.lower()

        # 找到关键词位置
        pos = content_lower.find(query_lower)
        if pos == -1:
            return content[:length]

        # 提取前后文
        start = max(0, pos - length // 2)
        end = min(len(content), pos + len(query) + length // 2)

        snippet = content[start:end]

        # 添加省略号
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet


class KnowledgeIndexTool(BaseTool):
    """
    知识库索引工具

    索引知识库结构
    """

    name = "knowledge_index"
    description = "获取知识库结构和索引"
    version = "1.0.0"
    parameters = [
        ToolParameter(
            name="folder",
            type=ParameterType.STRING,
            description="特定文件夹",
            required=False,
            default=""
        )
    ]

    VAULT_PATH = "C:/Users/13400/Documents/Obsidian/MyVault"

    async def execute(self, folder: str = "") -> ToolResult:
        """执行索引"""
        try:
            index_path = Path(self.VAULT_PATH)
            if folder:
                index_path = index_path / folder

            if not index_path.exists():
                return ToolResult.error_result(
                    error=f"路径不存在: {index_path}"
                )

            # 收集文件结构
            files = []
            for file_path in index_path.rglob("*.md"):
                rel_path = file_path.relative_to(self.VAULT_PATH)
                files.append({
                    "name": file_path.stem,
                    "path": str(rel_path),
                    "folder": str(rel_path.parent),
                    "size": file_path.stat().st_size
                })

            # 按文件夹分组
            folders = {}
            for f in files:
                folder_name = f["folder"]
                if folder_name not in folders:
                    folders[folder_name] = []
                folders[folder_name].append(f)

            return ToolResult.success_result(
                output=f"索引完成，共 {len(files)} 个文档",
                data={
                    "total_files": len(files),
                    "folders": folders,
                    "files": files
                }
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"索引失败: {str(e)}"
            )

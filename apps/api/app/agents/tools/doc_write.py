#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档写入工具

支持写入 Obsidian 知识库或本地文件
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from .base import BaseTool, ToolParameter, ToolResult, ParameterType


class DocumentWriteTool(BaseTool):
    """
    文档写入工具

    将内容写入 Obsidian 知识库或本地文件
    """

    name = "doc_write"
    description = "将内容写入文档（支持 Obsidian 知识库）"
    version = "1.0.0"
    parameters = [
        ToolParameter(
            name="content",
            type=ParameterType.STRING,
            description="文档内容",
            required=True
        ),
        ToolParameter(
            name="filename",
            type=ParameterType.STRING,
            description="文件名（不含路径）",
            required=True
        ),
        ToolParameter(
            name="folder",
            type=ParameterType.STRING,
            description="文件夹路径（相对知识库根目录）",
            required=False,
            default=""
        ),
        ToolParameter(
            name="append",
            type=ParameterType.BOOLEAN,
            description="是否追加模式",
            required=False,
            default=False
        )
    ]

    # Obsidian 知识库路径
    OBSIDIAN_VAULT_PATH = "C:/Users/13400/Documents/Obsidian/MyVault"

    async def execute(
        self,
        content: str,
        filename: str,
        folder: str = "",
        append: bool = False
    ) -> ToolResult:
        """
        执行文档写入

        Args:
            content: 文档内容
            filename: 文件名
            folder: 文件夹路径
            append: 是否追加

        Returns:
            ToolResult: 写入结果
        """
        try:
            # 构建完整路径
            full_path = self._build_path(filename, folder)

            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            mode = "a" if append else "w"
            with open(full_path, mode, encoding="utf-8") as f:
                if append:
                    f.write("\n\n")
                f.write(content)

            # 生成 Obsidian URI
            obsidian_uri = self._generate_obsidian_uri(filename, folder)

            return ToolResult.success_result(
                output=f"文档已保存: {full_path}",
                data={
                    "file_path": str(full_path),
                    "filename": filename,
                    "folder": folder,
                    "size": len(content),
                    "obsidian_uri": obsidian_uri
                }
            )

        except Exception as e:
            return ToolResult.error_result(
                error=f"写入失败: {str(e)}"
            )

    def _build_path(self, filename: str, folder: str) -> Path:
        """构建完整路径"""
        # 确保文件名有 .md 后缀
        if not filename.endswith(".md"):
            filename += ".md"

        if folder:
            return Path(self.OBSIDIAN_VAULT_PATH) / folder / filename
        return Path(self.OBSIDIAN_VAULT_PATH) / filename

    def _generate_obsidian_uri(self, filename: str, folder: str) -> str:
        """生成 Obsidian URI"""
        # 移除 .md 后缀用于 URI
        name = filename.replace(".md", "")
        if folder:
            return f"obsidian://open?vault=MyVault&file={folder}/{name}"
        return f"obsidian://open?vault=MyVault&file={name}"


class DocumentReadTool(BaseTool):
    """
    文档读取工具

    从 Obsidian 知识库或本地文件读取内容
    """

    name = "doc_read"
    description = "读取文档内容"
    version = "1.0.0"
    parameters = [
        ToolParameter(
            name="filename",
            type=ParameterType.STRING,
            description="文件名",
            required=True
        ),
        ToolParameter(
            name="folder",
            type=ParameterType.STRING,
            description="文件夹路径",
            required=False,
            default=""
        )
    ]

    OBSIDIAN_VAULT_PATH = "C:/Users/13400/Documents/Obsidian/MyVault"

    async def execute(
        self,
        filename: str,
        folder: str = ""
    ) -> ToolResult:
        """执行文档读取"""
        try:
            # 构建完整路径
            if not filename.endswith(".md"):
                filename += ".md"

            if folder:
                full_path = Path(self.OBSIDIAN_VAULT_PATH) / folder / filename
            else:
                full_path = Path(self.OBSIDIAN_VAULT_PATH) / filename

            # 读取文件
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return ToolResult.success_result(
                output=f"成功读取文档: {filename}",
                data={
                    "file_path": str(full_path),
                    "filename": filename,
                    "content": content,
                    "size": len(content)
                }
            )

        except FileNotFoundError:
            return ToolResult.error_result(
                error=f"文件不存在: {filename}"
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"读取失败: {str(e)}"
            )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian 知识库集成

提供与 Obsidian Vault 的读写集成
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'


from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ObsidianIntegration:
    """
    Obsidian 知识库集成

    支持：
    1. 写入文档到 Vault
    2. 读取 Vault 文档
    3. 搜索 Vault 内容
    4. 生成 Obsidian URI
    """

    def __init__(self, vault_path: Optional[str] = None):
        """
        初始化 Obsidian 集成

        Args:
            vault_path: Vault 路径，默认使用用户配置
        """
        self.vault_path = Path(vault_path or "C:/Users/13400/Documents/Obsidian/MyVault")
        self.vault_name = self.vault_path.name

    async def write_document(
        self,
        content: str,
        filename: str,
        folder: str = "04-项目层/Agent生成",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        写入文档到 Obsidian

        Args:
            content: 文档内容
            filename: 文件名（不含扩展名）
            folder: 文件夹路径
            metadata: 前置元数据

        Returns:
            写入结果
        """
        try:
            # 确保文件名有效
            filename = self._sanitize_filename(filename)
            if not filename.endswith(".md"):
                filename += ".md"

            # 构建完整路径
            file_path = self.vault_path / folder / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加前置元数据
            full_content = self._add_frontmatter(content, metadata)

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            # 生成 Obsidian URI
            obsidian_uri = self._generate_uri(folder, filename.replace(".md", ""))

            return {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "folder": folder,
                "obsidian_uri": obsidian_uri,
                "size": len(full_content)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def read_document(self, filename: str, folder: str = "") -> Dict[str, Any]:
        """读取文档"""
        try:
            if not filename.endswith(".md"):
                filename += ".md"

            if folder:
                file_path = self.vault_path / folder / filename
            else:
                file_path = self.vault_path / filename

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析前置元数据
            metadata, body = self._parse_frontmatter(content)

            return {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "metadata": metadata,
                "content": body
            }

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"File not found: {filename}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def search_documents(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索文档"""
        results = []
        query_lower = query.lower()

        try:
            for file_path in self.vault_path.rglob("*.md"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if query_lower in content.lower():
                        # 提取摘要
                        snippet = self._extract_snippet(content, query)

                        rel_path = file_path.relative_to(self.vault_path)

                        results.append({
                            "filename": file_path.stem,
                            "path": str(rel_path),
                            "folder": str(rel_path.parent),
                            "snippet": snippet,
                            "obsidian_uri": self._generate_uri(
                                str(rel_path.parent),
                                file_path.stem
                            )
                        })

                        if len(results) >= limit:
                            break

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Search error: {e}")

        return results

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        # 移除或替换非法字符
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()

    def _add_frontmatter(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """添加前置元数据"""
        if metadata is None:
            metadata = {}

        # 添加默认字段
        if "created" not in metadata:
            metadata["created"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if "source" not in metadata:
            metadata["source"] = "Jarvis PM Agent"

        # 构建 frontmatter
        frontmatter = "---\n"
        for key, value in metadata.items():
            if isinstance(value, list):
                frontmatter += f"{key}:\n"
                for item in value:
                    frontmatter += f"  - {item}\n"
            else:
                frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"

        return frontmatter + content

    def _parse_frontmatter(self, content: str) -> tuple:
        """解析前置元数据"""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            import yaml
            metadata = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return metadata or {}, body
        except Exception:
            return {}, content

    def _extract_snippet(self, content: str, query: str, length: int = 150) -> str:
        """提取摘要"""
        pos = content.lower().find(query.lower())
        if pos == -1:
            return content[:length]

        start = max(0, pos - length // 2)
        end = min(len(content), pos + len(query) + length // 2)
        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def _generate_uri(self, folder: str, filename: str) -> str:
        """生成 Obsidian URI"""
        path = f"{folder}/{filename}" if folder else filename
        return f"obsidian://open?vault={self.vault_name}&file={path}"

    async def save_agent_output(
        self,
        agent_name: str,
        product_name: str,
        content: str,
        output_type: str = "prd"
    ) -> Dict[str, Any]:
        """
        保存 Agent 输出到 Obsidian

        Args:
            agent_name: Agent 名称
            product_name: 产品名称
            content: 输出内容
            output_type: 输出类型

        Returns:
            保存结果
        """
        # 构建文件名
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{product_name}_{output_type}_{timestamp}"

        # 构建元数据
        metadata = {
            "agent": agent_name,
            "product": product_name,
            "type": output_type,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": ["agent-generated", output_type, product_name.lower().replace(" ", "-")]
        }

        return await self.write_document(
            content=content,
            filename=filename,
            folder=f"04-项目层/Agent生成/{product_name}",
            metadata=metadata
        )
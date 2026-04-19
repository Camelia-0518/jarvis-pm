#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成服务 - 端到端PRD生成功能

整合所有组件，提供完整的PRD生成、存储和导出功能
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.agents.agents.prd_agent import PRDAgent
from app.agents.templates import get_template_system, IndustryType
from app.agents.integrations.obsidian import ObsidianIntegration
from app.agents.persistence import get_persistence, WorkflowState
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class PRDGeneratorService:
    """
    PRD 生成服务

    提供从需求输入到PRD输出的完整流程
    """

    def __init__(self):
        self.prd_agent = PRDAgent()
        self.template_system = get_template_system()
        self.obsidian = ObsidianIntegration()
        self.persistence = get_persistence()

    async def generate_prd(
        self,
        product_name: str,
        description: str,
        target_users: Optional[str] = None,
        key_features: Optional[List[str]] = None,
        industry: Optional[str] = None,
        template_id: Optional[str] = None,
        save_to_obsidian: bool = True,
        save_local: bool = True
    ) -> Dict[str, Any]:
        """
        生成完整PRD

        Args:
            product_name: 产品名称
            description: 产品描述/需求
            target_users: 目标用户（可选）
            key_features: 核心功能列表（可选）
            industry: 行业类型（可选，自动检测）
            template_id: 指定模板ID（可选）
            save_to_obsidian: 是否保存到Obsidian
            save_local: 是否保存到本地

        Returns:
            包含PRD内容和元数据的字典
        """
        start_time = datetime.now()

        # 1. 自动检测行业类型
        if not industry:
            detected_industry = self.template_system.detect_industry(description)
            industry = detected_industry.value if detected_industry != IndustryType.UNKNOWN else "unknown"

        logger.info(f"[PRD Generator] 检测到行业类型: {industry}")

        # 2. 匹配模板
        template = None
        if template_id:
            template = self.template_system.get_template(template_id)
        else:
            template = self.template_system.match_template(description)

        if template:
            logger.info(f"[PRD Generator] 使用模板: {template.name}")

        # 3. 构建Agent输入
        agent_input = {
            "product_name": product_name,
            "description": description,
            "target_users": target_users or self._extract_target_users(description),
            "key_features": key_features or self._extract_key_features(description),
            "industry": industry,
            "template": template.id if template else None
        }

        # 4. 生成PRD
        logger.info("[PRD Generator] 开始生成PRD...")
        result = await self.prd_agent.execute(agent_input)

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }

        prd_content = result.output

        # 5. 应用医疗行业模板增强
        if template and industry == "medical":
            prd_content = self._enhance_medical_prd(prd_content, template)

        # 6. 生成元数据
        metadata = {
            "product_name": product_name,
            "industry": industry,
            "template_used": template.id if template else None,
            "generated_at": datetime.now().isoformat(),
            "content_length": len(prd_content),
            "execution_time": (datetime.now() - start_time).total_seconds()
        }

        # 7. 保存到Obsidian
        obsidian_result = None
        if save_to_obsidian:
            obsidian_result = await self._save_to_obsidian(
                product_name=product_name,
                content=prd_content,
                metadata=metadata,
                template=template
            )
            metadata["obsidian_path"] = obsidian_result.get("file_path") if obsidian_result.get("success") else None

        # 8. 保存到本地
        local_path = None
        if save_local:
            local_path = self._save_local(product_name, prd_content, metadata)
            metadata["local_path"] = local_path

        return {
            "success": True,
            "content": prd_content,
            "metadata": metadata,
            "obsidian_result": obsidian_result,
            "local_path": local_path,
            "execution_time": metadata["execution_time"]
        }

    async def generate_prd_with_chapters(
        self,
        product_name: str,
        description: str,
        chapters: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        按章节生成PRD

        Args:
            product_name: 产品名称
            description: 产品描述
            chapters: 指定章节列表（可选）
            **kwargs: 其他参数

        Returns:
            包含各章节内容的字典
        """
        default_chapters = [
            "background",
            "user_stories",
            "business_process",
            "functional_requirements",
            "data_requirements",
            "compliance_requirements",
            "data_tracking",
            "milestones"
        ]

        chapters = chapters or default_chapters
        chapter_contents = {}

        for chapter in chapters:
            logger.info(f"[PRD Generator] 生成章节: {chapter}")
            try:
                content = await self.prd_agent.generate_section(
                    section_name=chapter,
                    context={
                        "product_name": product_name,
                        "description": description,
                        **kwargs
                    }
                )
                chapter_contents[chapter] = content
            except Exception as e:
                chapter_contents[chapter] = f"生成失败: {str(e)}"

        # 合并所有章节
        full_content = self._merge_chapters(product_name, chapter_contents)

        return {
            "success": True,
            "chapters": chapter_contents,
            "full_content": full_content,
            "chapter_count": len(chapters)
        }

    def _extract_target_users(self, description: str) -> str:
        """从描述中提取目标用户"""
        # 简单规则：查找"用户"、"患者"、"医生"等关键词
        user_patterns = [
            r"患者",
            r"医生",
            r"护士",
            r"管理员",
            r"用户",
            r"客户",
            r"医护人员"
        ]

        users = []
        for pattern in user_patterns:
            if pattern in description:
                users.append(pattern)

        return "、".join(users) if users else "待确定"

    def _extract_key_features(self, description: str) -> List[str]:
        """从描述中提取核心功能"""
        # 简单规则：按标点符号分割，提取包含"功能"、"模块"等的句子
        sentences = re.split(r'[。；\n]', description)
        features = []

        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence for keyword in ["功能", "模块", "可以", "支持", "实现"]):
                if len(sentence) > 5 and len(sentence) < 100:
                    features.append(sentence)

        return features[:5] if features else ["核心功能待细化"]

    def _enhance_medical_prd(self, content: str, template) -> str:
        """增强医疗行业PRD内容"""
        # 检查是否已有合规章节
        if "## 7. 合规与安全要求" in content or "## 合规" in content:
            return content

        # 添加医疗合规章节
        compliance_section = self._generate_compliance_section(template)

        # 在文档末尾添加合规章节
        content = content.rstrip() + "\n\n" + compliance_section

        return content

    def _generate_compliance_section(self, template) -> str:
        """生成合规章节"""
        section = "## 7. 合规与安全要求\n\n"
        section += "> 本章节根据医疗行业合规要求自动生成\n\n"

        for req in template.compliance_requirements:
            section += f"### 7.{template.compliance_requirements.index(req) + 1} {req.name}\n\n"
            section += f"**描述**: {req.description}\n\n"
            section += f"**优先级**: {req.priority}\n\n"
            section += "**检查清单**:\n\n"

            for item in req.checklist:
                section += f"- [ ] {item}\n"

            section += "\n"

        return section

    async def _save_to_obsidian(
        self,
        product_name: str,
        content: str,
        metadata: Dict[str, Any],
        template=None
    ) -> Dict[str, Any]:
        """保存到Obsidian"""
        try:
            # 构建元数据
            obsidian_metadata = {
                "title": product_name,
                "type": "PRD",
                "industry": metadata.get("industry", "general"),
                "template": template.name if template else "default",
                "generated_at": metadata.get("generated_at"),
                "tags": [
                    "prd",
                    "agent-generated",
                    metadata.get("industry", "general"),
                    product_name.lower().replace(" ", "-")
                ]
            }

            # 确定文件夹
            folder = "04-项目层/Agent生成"
            if metadata.get("industry") == "medical":
                folder = "04-项目层/Agent生成/医疗项目"

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{product_name}_PRD_{timestamp}"

            result = await self.obsidian.write_document(
                content=content,
                filename=filename,
                folder=folder,
                metadata=obsidian_metadata
            )

            logger.info(f"[PRD Generator] 已保存到Obsidian: {result.get('file_path', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"[PRD Generator] 保存到Obsidian失败: {e}")
            return {"success": False, "error": str(e)}

    def _save_local(self, product_name: str, content: str, metadata: Dict[str, Any]) -> str:
        """保存到本地文件"""
        try:
            # 创建输出目录
            output_dir = Path.home() / ".jarvis" / "prd_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{product_name.replace(' ', '_')}_PRD_{timestamp}.md"
            file_path = output_dir / filename

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                # 添加元数据头部
                f.write("---\n")
                f.write(f"title: {product_name}\n")
                f.write(f"type: PRD\n")
                f.write(f"industry: {metadata.get('industry', 'general')}\n")
                f.write(f"generated_at: {metadata.get('generated_at')}\n")
                f.write(f"execution_time: {metadata.get('execution_time', 0):.2f}s\n")
                f.write("---\n\n")
                f.write(content)

            logger.info(f"[PRD Generator] 已保存到本地: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"[PRD Generator] 保存到本地失败: {e}")
            return ""

    def _merge_chapters(self, product_name: str, chapters: Dict[str, str]) -> str:
        """合并各章节为完整PRD"""
        content = f"# {product_name} - 产品需求文档 (PRD)\n\n"
        content += f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "---\n\n"

        chapter_titles = {
            "background": "1. 背景与目标",
            "user_stories": "2. 用户故事",
            "business_process": "3. 业务流程",
            "functional_requirements": "4. 功能规格",
            "data_requirements": "5. 数据需求",
            "compliance_requirements": "6. 合规要求",
            "data_tracking": "7. 数据埋点",
            "milestones": "8. 里程碑"
        }

        for chapter_key, chapter_content in chapters.items():
            title = chapter_titles.get(chapter_key, chapter_key)
            content += f"\n## {title}\n\n"
            content += chapter_content
            content += "\n\n"

        return content

    def export_prd(
        self,
        content: str,
        format: str = "markdown",
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        导出PRD到不同格式

        Args:
            content: PRD内容
            format: 导出格式 (markdown, json, feishu)
            filename: 文件名（可选）

        Returns:
            导出结果
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"PRD_{timestamp}"

        if format == "markdown":
            return {
                "success": True,
                "content": content,
                "filename": f"{filename}.md",
                "format": "markdown"
            }

        elif format == "json":
            # 解析Markdown为结构化数据
            structured_data = self._parse_markdown_to_json(content)
            return {
                "success": True,
                "content": json.dumps(structured_data, ensure_ascii=False, indent=2),
                "filename": f"{filename}.json",
                "format": "json"
            }

        elif format == "feishu":
            # 转换为飞书文档格式
            feishu_content = self._convert_to_feishu(content)
            return {
                "success": True,
                "content": feishu_content,
                "filename": f"{filename}_feishu.md",
                "format": "feishu"
            }

        else:
            return {
                "success": False,
                "error": f"不支持的格式: {format}"
            }

    def _parse_markdown_to_json(self, content: str) -> Dict[str, Any]:
        """解析Markdown为JSON结构"""
        lines = content.split('\n')
        result = {
            "title": "",
            "sections": []
        }

        current_section = None
        current_content = []

        for line in lines:
            if line.startswith('# '):
                result["title"] = line.replace('# ', '').strip()
            elif line.startswith('## '):
                if current_section:
                    result["sections"].append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip()
                    })
                current_section = line.replace('## ', '').strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section:
            result["sections"].append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })

        return result

    def _convert_to_feishu(self, content: str) -> str:
        """转换为飞书文档格式"""
        # 飞书文档支持标准Markdown，添加一些特定格式
        feishu_content = content

        # 添加飞书文档头部
        header = """---
document_type: feishu
version: 1.0
---

"""

        return header + feishu_content


# 全局服务实例
prd_generator_service = PRDGeneratorService()

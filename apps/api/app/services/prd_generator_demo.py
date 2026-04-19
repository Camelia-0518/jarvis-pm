#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRD 生成服务 - 演示模式

在没有 API 的情况下生成示例 PRD 内容，用于演示和测试
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from app.agents.templates import get_template_system, IndustryType
from app.agents.integrations.obsidian import ObsidianIntegration

logger = logging.getLogger(__name__)


class PRDGeneratorDemoService:
    """
    PRD 生成服务 - 演示模式

    在没有 AI API 的情况下生成示例 PRD 内容
    """

    def __init__(self):
        self.template_system = get_template_system()
        self.obsidian = ObsidianIntegration()

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
        生成示例 PRD（演示模式）
        """
        start_time = datetime.now()

        # 1. 自动检测行业类型
        if not industry:
            detected_industry = self.template_system.detect_industry(description)
            industry = detected_industry.value if detected_industry != IndustryType.UNKNOWN else "general"

        logger.info(f"[PRD Generator Demo] 检测到行业类型: {industry}")

        # 2. 匹配模板
        template = None
        if template_id:
            template = self.template_system.get_template(template_id)
        else:
            template = self.template_system.match_template(description)

        if template:
            logger.info(f"[PRD Generator Demo] 使用模板: {template.name}")

        # 3. 生成示例 PRD 内容
        prd_content = self._generate_demo_prd(
            product_name=product_name,
            description=description,
            target_users=target_users or "待确定",
            key_features=key_features or ["核心功能待细化"],
            industry=industry,
            template=template
        )

        # 4. 生成元数据
        metadata = {
            "product_name": product_name,
            "industry": industry,
            "template_used": template.id if template else None,
            "generated_at": datetime.now().isoformat(),
            "content_length": len(prd_content),
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "mode": "demo"  # 标记为演示模式
        }

        # 5. 保存到Obsidian
        obsidian_result = None
        if save_to_obsidian:
            obsidian_result = await self._save_to_obsidian(
                product_name=product_name,
                content=prd_content,
                metadata=metadata,
                template=template
            )
            metadata["obsidian_path"] = obsidian_result.get("file_path") if obsidian_result.get("success") else None

        # 6. 保存到本地
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
            "execution_time": metadata["execution_time"],
            "note": "这是演示模式生成的示例PRD，实际使用时请配置AI API"
        }

    def _generate_demo_prd(
        self,
        product_name: str,
        description: str,
        target_users: str,
        key_features: List[str],
        industry: str,
        template=None
    ) -> str:
        """生成示例 PRD 内容"""

        content = f"""---
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
mode: demo
agent: prd_generator v1.0.0
---

# {product_name} - 产品需求文档 (PRD)

> **注意**: 这是演示模式生成的示例PRD，展示了标准PRD结构和医疗行业合规章节。
> 实际使用时请配置 AI API (KIMI_API_KEY) 以生成真实内容。

---

## 1. 背景与目标

### 1.1 产品背景

{description}

### 1.2 业务目标

- 提高业务效率，降低运营成本
- 改善用户体验，提升满意度
- 实现数字化转型

### 1.3 成功指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| 使用率 | > 80% | 系统统计 |
| 完成率 | > 90% | 业务统计 |
| 满意度 | > 4.5/5 | 用户调研 |

---

## 2. 用户故事

### 2.1 目标用户

{target_users}

### 2.2 用户故事列表

"""

        # 添加用户故事
        for i, feature in enumerate(key_features[:5], 1):
            content += f"""
#### US-{i:02d}: {feature}

- **作为** {target_users.split('、')[0] if '、' in target_users else '用户'}
- **我想要** {feature}
- **以便** 提高工作效率/获得更好体验

**验收标准**:
- [ ] 功能可用且稳定
- [ ] 响应时间 < 3秒
- [ ] 错误率 < 1%

"""

        content += f"""
---

## 3. 业务流程

### 3.1 核心业务流程

```
开始 -> 用户操作 -> 系统处理 -> 结果反馈 -> 结束
```

### 3.2 异常流程

- 网络异常：提示用户检查网络
- 数据异常：记录日志并通知管理员
- 权限异常：引导用户申请权限

---

## 4. 功能规格

### 4.1 功能列表

| 功能模块 | 功能点 | 优先级 | 状态 |
|----------|--------|--------|------|
"""

        for i, feature in enumerate(key_features[:5], 1):
            content += f"| 模块{i} | {feature} | P{i if i <= 2 else 3} | 规划中 |\n"

        content += f"""
### 4.2 功能详情

#### 功能1: {key_features[0] if key_features else '核心功能'}

**功能描述**:
详细描述该功能的具体实现逻辑...

**输入**:
- 输入项1: 说明
- 输入项2: 说明

**输出**:
- 输出项1: 说明
- 输出项2: 说明

**业务规则**:
1. 规则1
2. 规则2
3. 规则3

---

## 5. 数据需求

### 5.1 数据模型

| 实体 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 用户 | user_id | String | 用户唯一标识 |
| 用户 | name | String | 用户姓名 |
| 用户 | created_at | DateTime | 创建时间 |

### 5.2 数据流转

```
用户输入 -> 前端校验 -> 后端处理 -> 数据存储 -> 结果返回
```

---

"""

        # 添加医疗合规章节（如果是医疗行业）
        if industry == "medical" and template:
            content += self._generate_compliance_section(template)
        else:
            content += f"""
## 6. 合规要求

### 6.1 通用合规

- [ ] 用户隐私保护
- [ ] 数据安全存储
- [ ] 操作日志记录
- [ ] 权限控制

---

"""

        content += f"""
## 7. 数据埋点

### 7.1 埋点事件

| 事件名称 | 触发时机 | 事件属性 |
|----------|----------|----------|
| page_view | 页面浏览 | page_name, user_id |
| button_click | 按钮点击 | button_name, context |
| form_submit | 表单提交 | form_name, result |

### 7.2 分析指标

- 日活跃用户数 (DAU)
- 功能使用率
- 用户留存率
- 平均使用时长

---

## 8. 里程碑

### 8.1 项目计划

| 阶段 | 时间 | 交付物 | 负责人 |
|------|------|--------|--------|
| Phase 1 | 第1-2周 | 需求确认、原型设计 | 产品经理 |
| Phase 2 | 第3-4周 | 开发实现、内部测试 | 开发团队 |
| Phase 3 | 第5-6周 | 用户测试、上线部署 | 运维团队 |

### 8.2 风险预案

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| 需求变更 | 中 | 高 | 敏捷迭代 |
| 技术难点 | 低 | 中 | 技术预研 |
| 资源不足 | 中 | 中 | 资源协调 |

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| PRD | 产品需求文档 (Product Requirement Document) |
| UI | 用户界面 (User Interface) |
| UX | 用户体验 (User Experience) |

### B. 参考文档

- 产品需求分析
- 竞品分析报告
- 用户调研报告

---

*本文档由 Jarvis PM 自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return content

    def _generate_compliance_section(self, template) -> str:
        """生成医疗合规章节"""
        section = "## 6. 合规与安全要求\n\n"
        section += "> **注意**: 本章节根据医疗行业合规要求自动生成，实际项目中请根据具体情况调整。\n\n"

        for idx, req in enumerate(template.compliance_requirements, 1):
            section += f"### 6.{idx} {req.name}\n\n"
            section += f"**描述**: {req.description}\n\n"
            section += f"**类别**: {req.category}\n\n"
            section += f"**优先级**: {req.priority}\n\n"
            section += "**检查清单**:\n\n"

            for item in req.checklist:
                section += f"- [ ] {item}\n"

            section += "\n"

        section += """### 6.6 合规检查总结

| 检查项 | 状态 | 备注 |
|--------|------|------|
| 等保三级合规 | 待评估 | 需安全团队评估 |
| 患者隐私保护 | 待评估 | 需法务团队审核 |
| 数据安全 | 待评估 | 需技术团队实现 |
| 操作审计 | 待评估 | 需产品团队设计 |
| 跨院区适配 | 待评估 | 如适用 |

---

"""
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
            obsidian_metadata = {
                "title": product_name,
                "type": "PRD",
                "industry": metadata.get("industry", "general"),
                "template": template.name if template else "default",
                "generated_at": metadata.get("generated_at"),
                "mode": "demo",
                "tags": [
                    "prd",
                    "agent-generated",
                    "demo",
                    metadata.get("industry", "general"),
                    product_name.lower().replace(" ", "-")
                ]
            }

            folder = "04-项目层/Agent生成/Demo"
            if metadata.get("industry") == "medical":
                folder = "04-项目层/Agent生成/Demo/医疗项目"

            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{product_name}_PRD_DEMO_{timestamp}"

            result = await self.obsidian.write_document(
                content=content,
                filename=filename,
                folder=folder,
                metadata=obsidian_metadata
            )

            logger.info(f"[PRD Generator Demo] 已保存到Obsidian: {result.get('file_path', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"[PRD Generator Demo] 保存到Obsidian失败: {e}")
            return {"success": False, "error": str(e)}

    def _save_local(self, product_name: str, content: str, metadata: Dict[str, Any]) -> str:
        """保存到本地文件"""
        try:
            output_dir = Path.home() / ".jarvis" / "prd_outputs" / "demo"
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{product_name.replace(' ', '_')}_PRD_DEMO_{timestamp}.md"
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("---\n")
                f.write(f"title: {product_name}\n")
                f.write(f"type: PRD\n")
                f.write(f"industry: {metadata.get('industry', 'general')}\n")
                f.write(f"generated_at: {metadata.get('generated_at')}\n")
                f.write(f"mode: demo\n")
                f.write(f"execution_time: {metadata.get('execution_time', 0):.2f}s\n")
                f.write("---\n\n")
                f.write(content)

            logger.info(f"[PRD Generator Demo] 已保存到本地: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"[PRD Generator Demo] 保存到本地失败: {e}")
            return ""

    def export_prd(
        self,
        content: str,
        format: str = "markdown",
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """导出PRD到不同格式"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"PRD_DEMO_{timestamp}"

        if format == "markdown":
            return {
                "success": True,
                "content": content,
                "filename": f"{filename}.md",
                "format": "markdown"
            }
        elif format == "json":
            structured_data = self._parse_markdown_to_json(content)
            return {
                "success": True,
                "content": json.dumps(structured_data, ensure_ascii=False, indent=2),
                "filename": f"{filename}.json",
                "format": "json"
            }
        elif format == "feishu":
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
        result = {"title": "", "sections": []}
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
        header = """---
document_type: feishu
version: 1.0
---

"""
        return header + content


# 全局演示服务实例
prd_generator_demo_service = PRDGeneratorDemoService()

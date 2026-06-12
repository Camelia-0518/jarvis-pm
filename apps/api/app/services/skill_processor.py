"""技能处理器

提供技能定义管理和执行功能。
"""

import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.services.skill_processor_enhanced import SkillProcessorEnhanced
from app.utils.json_helpers import extract_json_from_text, parse_json_output


class SkillProcessor:
    """技能处理器 - 管理技能定义和执行（兼容层，执行时委托给增强版处理器）"""

    def __init__(self):
        # 技能定义注册表
        self._skills: Dict[str, Dict[str, Any]] = {}
        # 增强版处理器（负责真实 LLM 调用、缓存、Schema 验证、医疗术语增强）
        self._enhanced = SkillProcessorEnhanced(enable_cache=True)
        self._init_skills()

    # 技能输出 Schema 和示例（与前端共享，消除重复定义）
    _OUTPUT_SCHEMAS: Dict[str, Dict[str, Any]] = {
        "requirement-analysis": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "productOneLiner": {"type": "string"},
                    "userPersona": {
                        "type": "object",
                        "properties": {
                            "who": {"type": "string"},
                            "painPoints": {"type": "string"},
                            "currentSolutions": {"type": "string"},
                            "whyNewProduct": {"type": "string"},
                        },
                    },
                    "featureList": {
                        "type": "object",
                        "properties": {
                            "p0": {"type": "array", "items": {"type": "string"}},
                            "p1": {"type": "array", "items": {"type": "string"}},
                            "p2": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "userStories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "role": {"type": "string"},
                                "action": {"type": "string"},
                                "benefit": {"type": "string"},
                                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                            },
                        },
                    },
                    "successMetrics": {
                        "type": "object",
                        "properties": {
                            "northStar": {"type": "string"},
                            "metrics": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "target": {"type": "string"},
                                        "timeFrame": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
                "required": ["productOneLiner", "userPersona", "featureList", "userStories", "successMetrics"],
            },
            "examples": [
                {
                    "id": "medical-record-copy",
                    "name": "病案复印系统",
                    "description": "医院病历在线申请复印系统",
                    "inputs": {
                        "idea": "一个帮助患者在线申请病历复印并快递到家的系统",
                        "targetUsers": "医院患者、病案室工作人员",
                        "industry": "medical",
                    },
                    "outputPreview": "产品一句话描述：一个帮助患者在线申请病案复印并快递到家的医疗服务平台...",
                }
            ],
        },
        "write-prd": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "version": {"type": "string"},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                                "priority": {"type": "string"},
                            },
                        },
                    },
                    "markdown": {"type": "string"},
                },
            },
            "examples": [],
        },
        "medical-review": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "medicalRationality": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "assessment": {"type": "string"},
                            "concerns": {"type": "array", "items": {"type": "string"}},
                            "recommendations": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "complianceAnalysis": {
                        "type": "object",
                        "properties": {
                            "applicableRegulations": {"type": "array", "items": {"type": "string"}},
                            "complianceStatus": {"type": "string", "enum": ["compliant", "partial", "non-compliant"]},
                            "gaps": {"type": "array", "items": {"type": "string"}},
                            "actions": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "riskAssessment": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "risk": {"type": "string"},
                                "level": {"type": "string", "enum": ["high", "medium", "low"]},
                                "impact": {"type": "string"},
                                "mitigation": {"type": "string"},
                            },
                        },
                    },
                    "approvalRecommendation": {"type": "string", "enum": ["approve", "approve-with-conditions", "reject"]},
                },
            },
            "examples": [],
        },
        "compliance-check": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "overallStatus": {"type": "string", "enum": ["pass", "fail", "partial"]},
                    "score": {"type": "number"},
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {"type": "string", "enum": ["pass", "fail", "partial"]},
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "requirement": {"type": "string"},
                                            "status": {"type": "string", "enum": ["pass", "fail", "na"]},
                                            "evidence": {"type": "string"},
                                            "remediation": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "criticalIssues": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "checklist": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item": {"type": "string"},
                                "checked": {"type": "boolean"},
                                "category": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "examples": [],
        },
        "multi-branch-analysis": {
            "outputSchema": {
                "type": "object",
                "properties": {
                    "standardFeatures": {"type": "array", "items": {"type": "string"}},
                    "branchSpecific": {"type": "object"},
                    "policyDifferences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "aspect": {"type": "string"},
                                "standard": {"type": "string"},
                                "branches": {"type": "object"},
                            },
                        },
                    },
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
            },
            "examples": [],
        },
    }

    def reload_skills(self):
        """重新加载所有技能定义（支持热更新，无需重启进程）"""
        self._skills.clear()
        self._init_skills()
        return {"reloaded_at": datetime.now().isoformat(), "skill_count": len(self._skills)}

    def _init_skills(self):
        "从增强版处理器同步技能定义，消除重复定义"
        if not self._enhanced._skills:
            self._enhanced._init_skills()
        self._skills = dict(self._enhanced._skills)



    def _enrich_skill_metadata(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """丰富技能元数据，合并 outputSchema 和 examples"""
        result = {k: v for k, v in skill.items() if k != "prompt_template"}
        extra = self._OUTPUT_SCHEMAS.get(skill.get("id", ""), {})
        result.setdefault("outputSchema", extra.get("outputSchema", {}))
        result.setdefault("examples", extra.get("examples", []))
        return result

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """获取所有技能定义"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
        ]

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取技能定义"""
        skill = self._skills.get(skill_id)
        if skill:
            return self._enrich_skill_metadata(skill)
        return None

    def get_skill_prompt(self, skill_id: str) -> Optional[str]:
        """获取技能的提示词模板"""
        skill = self._skills.get(skill_id)
        return skill.get("prompt_template") if skill else None

    def get_skills_by_role(self, role: str) -> List[Dict[str, Any]]:
        """根据Agent角色获取技能"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
            if skill.get("agentRole") == role
        ]

    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据分类获取技能"""
        return [
            self._enrich_skill_metadata(skill)
            for skill in self._skills.values()
            if skill.get("category") == category
        ]

    def validate_inputs(self, skill_id: str, inputs: Dict[str, Any]) -> List[str]:
        """验证技能输入"""
        errors = []
        skill = self._skills.get(skill_id)

        if not skill:
            return [f"技能 {skill_id} 不存在"]

        parameters = skill.get("parameters", [])
        for param in parameters:
            if param.get("required"):
                param_name = param.get("name")
                value = inputs.get(param_name)
                if value is None or value == "":
                    errors.append(f"参数 '{param.get('label', param_name)}' 是必填项")

        return errors

    async def execute_skill(
        self,
        skill_id: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行技能

        Args:
            skill_id: 技能ID
            inputs: 输入参数
            context: 执行上下文
            options: 执行选项

        Returns:
            执行结果
        """
        start_time = time.time()

        # 验证技能存在
        skill = self._skills.get(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"技能 {skill_id} 不存在",
                "output": {},
            }

        # 获取提示词模板
        prompt_template = skill.get("prompt_template", "")

        # 为可选参数设置默认值（必须在验证前完成）
        parameters = skill.get("parameters", [])
        for param in parameters:
            param_name = param.get("name")
            if param_name not in inputs:
                if param.get("type") == "textarea":
                    inputs[param_name] = ""
                elif param.get("type") == "string":
                    inputs[param_name] = ""
                elif param.get("type") == "array":
                    inputs[param_name] = []
                elif param.get("type") == "boolean":
                    inputs[param_name] = param.get("defaultValue", False)
                elif param.get("type") == "number":
                    inputs[param_name] = param.get("defaultValue", 0)
                elif param.get("type") == "select":
                    inputs[param_name] = param.get("defaultValue", "")

        # 验证输入
        validation_errors = self.validate_inputs(skill_id, inputs)
        if validation_errors:
            return {
                "success": False,
                "error": "; ".join(validation_errors),
                "output": {},
            }

        try:
            # 优先委托给增强版处理器（支持真实 LLM、缓存、Schema 验证、医疗术语增强）
            if skill_id in self._enhanced._skills:
                # 使用新的 provider 重新创建 enhanced 实例，避免缓存旧的 mock provider
                from app.core.config import settings
                provider = settings.DEFAULT_AI_PROVIDER
                enhanced = SkillProcessorEnhanced(llm_provider=provider, enable_cache=True)
                enhanced_result = await enhanced.execute_skill(
                    skill_id=skill_id,
                    inputs=inputs,
                    context=context or {},
                    skip_cache=True
                )
                # 保持与旧接口兼容的字段映射
                return {
                    "success": enhanced_result.get("success", False),
                    "output": enhanced_result.get("output", {}),
                    "formatted_output": enhanced_result.get("formatted_output", "")
                                    or enhanced_result.get("formattedOutput", ""),
                    "execution_time": enhanced_result.get("execution_time", 0),
                    "token_usage": enhanced_result.get("token_usage", {}),
                    "error": enhanced_result.get("error"),
                }

            # 回退：使用旧版 AI 调用逻辑（用于增强版未注册的技能）
            prompt = prompt_template.format(**inputs)
            output = await self._call_ai_for_skill(skill, prompt, options)

            execution_time = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "output": output,
                "formatted_output": self._format_output_as_markdown(skill, output),
                "execution_time": execution_time,
                "token_usage": {
                    "prompt": len(prompt) // 4,
                    "completion": len(json.dumps(output)) // 4,
                    "total": (len(prompt) + len(json.dumps(output))) // 4,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": {},
            }

    async def _call_ai_for_skill(
        self,
        skill: Dict[str, Any],
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """调用真实 AI 服务执行技能"""
        from app.services.ai_service import ai_service

        skill_id = skill.get("id")
        skill_name = skill.get("name", "")

        try:
            # write-prd 使用更宽松的 system prompt，允许 markdown 回退
            if skill_id == "write-prd":
                system_prompt = f"""你是{skill_name}专家。请根据用户输入生成完整的产品需求文档。
优先以合法 JSON 格式返回，包含 title、version、sections、markdown 字段。
如果 JSON 输出会被截断，请确保 markdown 字段的内容完整且可用。
也可以直接输出 Markdown 格式的 PRD 正文。"""

                content = await ai_service.chat(
                    prompt,
                    context={"system_prompt": system_prompt, "max_tokens": 8000}
                )

                if not content or not content.strip():
                    raise Exception("AI 返回了空内容，请检查模型参数或稍后重试")

                raw = content.strip()

                # 如果以 { 开头，尝试 JSON 解析
                if raw.startswith("{"):
                    try:
                        # 尝试从 markdown 代码块中提取
                        json_raw = raw
                        if "```json" in json_raw:
                            json_raw = json_raw.split("```json")[1].split("```")[0]
                        elif "```" in json_raw:
                            json_raw = json_raw.split("```")[1].split("```")[0]
                        json_raw = json_raw.strip()
                        result = json.loads(json_raw)
                        if "markdown" in result:
                            return result
                    except (json.JSONDecodeError, Exception):
                        pass

                # 回退：将原始内容包装为 markdown
                return {
                    "title": "产品需求文档",
                    "version": "1.0",
                    "sections": [
                        {"title": "产品概述", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "用户画像", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "功能需求", "content": "详见 markdown 正文", "priority": "high"},
                        {"title": "非功能需求", "content": "详见 markdown 正文", "priority": "normal"},
                    ],
                    "markdown": raw,
                }

            # 其他 skill 保持严格的 JSON 解析
            system_prompt = f"""你是{skill_name}专家。请根据用户输入生成结构化结果。
必须以合法、完整的 JSON 格式返回，确保 JSON 结构闭合完整，不要截断。
只输出 JSON，不要添加 markdown 代码块标记或其他说明文字。"""

            content = await ai_service.chat(
                prompt,
                context={"system_prompt": system_prompt, "max_tokens": 8000}
            )

            if not content or not content.strip():
                raise Exception("AI 返回了空内容，请检查模型参数或稍后重试")

            # 使用共享工具提取并解析 JSON
            raw = extract_json_from_text(content)
            if not raw:
                raise Exception(f"AI 返回内容经清理后为空。原始内容: {repr(content[:200])}")

            return parse_json_output(content)
        except Exception as e:
            # 如果解析失败，抛出异常让上层感知技能执行失败
            error_detail = f"JSON解析失败: {str(e)}"
            if 'content' in locals() and content:
                # 记录原始内容的前500字符用于调试
                error_detail += f" | 原始内容预览: {content[:500]}"
            raise Exception(error_detail)

    def _format_output_as_markdown(self, skill: Dict[str, Any], output: Dict[str, Any]) -> str:
        """将输出格式化为 Markdown"""
        skill_name = skill.get("name", "")
        skill_id = skill.get("id", "")

        if skill_id == "requirement-analysis":
            return f"""## 需求分析结果

### 产品一句话描述
{output.get('productOneLiner', '')}

### 用户画像
- **用户是谁**: {output.get('userPersona', {}).get('who', '')}
- **痛点是什么**: {output.get('userPersona', {}).get('painPoints', '')}
- **当前解决方案**: {output.get('userPersona', {}).get('currentSolutions', '')}
- **为什么需要新产品**: {output.get('userPersona', {}).get('whyNewProduct', '')}

### 功能列表
**P0（必须有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p0', [])])}

**P1（应该有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p1', [])])}

**P2（可以有）:**
{chr(10).join(['- ' + f for f in output.get('featureList', {}).get('p2', [])])}
"""

        elif skill_id == "medical-review":
            return f"""## 医疗业务评审结果

### 评审结论
{output.get('approvalRecommendation', '')}

### 业务合理性评分
**{output.get('medicalRationality', {}).get('score', 0)}/100**

{output.get('medicalRationality', {}).get('assessment', '')}

### 合规性分析
**状态**: {output.get('complianceAnalysis', {}).get('complianceStatus', '')}

**适用法规**:
{chr(10).join(['- ' + r for r in output.get('complianceAnalysis', {}).get('applicableRegulations', [])])}
"""

        else:
            # 通用 Markdown 格式
            return f"## {skill_name} 执行结果\n\n```json\n{json.dumps(output, indent=2, ensure_ascii=False)}\n```"


# 导出单例实例
skill_processor = SkillProcessor()

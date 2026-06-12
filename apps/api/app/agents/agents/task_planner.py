#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务规划 Agent

将高层意图分解为可执行的任务链
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..templates import TemplateSystem, IndustryType, get_template_system

from ..base import BaseAgent, AgentResult, AgentState


@dataclass
class TaskStep:
    """任务步骤"""
    id: str
    agent_name: str
    description: str
    input_data: Dict[str, Any]
    dependencies: List[str]  # 依赖的步骤ID
    estimated_time: int  # 估计执行时间（秒）


class TaskPlanner(BaseAgent):
    """
    任务规划 Agent

    根据意图识别结果，生成可执行的任务计划
    """

    name = "task_planner"
    description = "将用户意图分解为可执行的任务链"
    version = "1.0.0"
    capabilities = [
        "task_decomposition",
        "workflow_planning",
        "dependency_management"
    ]

    # 预定义的工作流模板
    WORKFLOW_TEMPLATES = {
        "requirement_analysis": {
            "name": "需求分析流程",
            "steps": [
                {"agent": "requirement_analyzer", "description": "分析用户需求", "estimated_time": 120}
            ]
        },
        "competitor_analysis": {
            "name": "竞品分析流程",
            "steps": [
                {"agent": "competitor_analyst", "description": "搜索并分析竞品", "estimated_time": 180}
            ]
        },
        "prd_only": {
            "name": "PRD生成流程",
            "steps": [
                {"agent": "prd_generator", "description": "生成产品需求文档", "estimated_time": 180}
            ]
        },
        "full_workflow": {
            "name": "完整产品开发流程",
            "steps": [
                {"agent": "requirement_analyzer", "description": "分析用户需求", "estimated_time": 120},
                {"agent": "competitor_analyst", "description": "分析竞品", "estimated_time": 180},
                {"agent": "prd_generator", "description": "生成PRD文档", "estimated_time": 180},
                {"agent": "compliance_checker", "description": "合规检查", "estimated_time": 120}
            ]
        },
        "medical_product": {
            "name": "医疗产品专用流程",
            "steps": [
                {"agent": "requirement_analyzer", "description": "分析需求", "estimated_time": 120},
                {"agent": "competitor_analyst", "description": "分析竞品", "estimated_time": 180},
                {"agent": "compliance_checker", "description": "医疗合规检查", "estimated_time": 180},
                {"agent": "prd_generator", "description": "生成合规PRD", "estimated_time": 180}
            ]
        }
    }

    SYSTEM_PROMPT = """你是任务规划专家。根据用户需求和意图，设计最优的任务执行计划。

规划原则：
1. 任务分解要合理，每个步骤可独立执行
2. 考虑步骤间的依赖关系
3. 预估每个步骤的执行时间
4. 选择最合适的Agent执行每个步骤

输出格式为JSON：
{
    "workflow_name": "工作流名称",
    "total_steps": 3,
    "estimated_total_time": 300,
    "steps": [
        {
            "id": "step_1",
            "agent_name": "agent_name",
            "description": "步骤描述",
            "input_data": {},
            "dependencies": [],
            "estimated_time": 120
        }
    ]
}"""

    def __init__(self, llm_client=None, **kwargs):
        super().__init__(llm_client=llm_client, **kwargs)
        self.template_system = get_template_system()

    async def _do_execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        执行任务规划

        Args:
            input_data: 包含 intent_result（意图识别结果）

        Returns:
            AgentResult: 包含任务计划
        """
        intent_result = input_data.get("intent_result", {})
        user_input = input_data.get("user_input", "")
        context = input_data.get("context", {})

        # 步骤1: 选择工作流模板
        step1 = self._create_step("select_template", "选择工作流模板")
        workflow_type = self._select_workflow(intent_result)
        self._complete_step(step1, f"选择模板: {workflow_type}")

        # 步骤2: 检测行业并匹配模板
        step2 = self._create_step("detect_industry", "检测行业类型")
        industry = self.template_system.detect_industry(user_input)
        template = self.template_system.match_template(user_input, industry)
        self._complete_step(step2, f"检测到行业: {industry.value}, 模板: {template.name if template else '无'}")

        # 步骤3: 生成详细计划
        step3 = self._create_step("generate_plan", "生成详细计划")
        plan = await self._generate_plan(
            workflow_type=workflow_type,
            intent_result=intent_result,
            user_input=user_input,
            context=context,
            template=template
        )
        self._complete_step(step3, f"生成 {len(plan['steps'])} 个步骤")

        # 步骤4: 应用模板增强（如果有）
        step4 = self._create_step("apply_template", "应用行业模板")
        if template:
            plan = self.template_system.apply_template_to_plan(template, plan)
            self._complete_step(step4, f"应用模板: {template.name}")
        else:
            self._complete_step(step4, "无匹配模板")

        # 步骤5: 验证计划
        step5 = self._create_step("validate_plan", "验证计划")
        validation = self._validate_plan(plan)
        self._complete_step(step5, f"验证结果: {validation['status']}")

        # 构建返回数据
        result_data = {
            "workflow_type": workflow_type,
            "plan": plan,
            "validation": validation,
            "industry": industry.value
        }

        # 如果有模板，添加模板信息
        if template:
            result_data["template"] = {
                "id": template.id,
                "name": template.name,
                "industry": template.industry.value
            }

        return AgentResult(
            success=True,
            output=f"生成任务计划: {plan['workflow_name']}，共 {len(plan['steps'])} 个步骤",
            data=result_data,
            execution_time=self.elapsed_seconds,
            metadata={
                "agent_name": self.name,
                "total_estimated_time": plan.get("estimated_total_time", 0),
                "industry": industry.value,
                "template_id": template.id if template else None
            }
        )

    def _select_workflow(self, intent_result: Dict[str, Any]) -> str:
        """根据意图选择工作流模板"""
        task_type = intent_result.get("task_type", "unknown")
        entities = intent_result.get("entities", {})
        industry = entities.get("industry", "").lower()

        # 医疗行业特殊处理
        if "医疗" in industry or "医院" in industry or "病理" in industry:
            return "medical_product"

        # 根据任务类型选择
        workflow_map = {
            "requirement_analysis": "requirement_analysis",
            "competitor_analysis": "competitor_analysis",
            "prd_generation": "prd_only",
            "full_workflow": "full_workflow",
            "compliance_check": "medical_product",
            "review_preparation": "full_workflow"
        }

        return workflow_map.get(task_type, "full_workflow")

    async def _generate_plan(
        self,
        workflow_type: str,
        intent_result: Dict[str, Any],
        user_input: str,
        context: Dict[str, Any],
        template: Optional[Any] = None
    ) -> Dict[str, Any]:
        """生成详细任务计划"""

        # 获取模板
        template = self.WORKFLOW_TEMPLATES.get(workflow_type, self.WORKFLOW_TEMPLATES["full_workflow"])

        # 构建基础输入数据
        entities = intent_result.get("entities", {})
        base_input = {
            "product_name": entities.get("product_name", context.get("product_name", "未命名产品")),
            "description": user_input,
            "target_users": entities.get("target_users", ""),
            "key_features": entities.get("key_features", []),
            "industry": entities.get("industry", ""),
            "constraints": entities.get("constraints", [])
        }

        # 生成步骤
        steps = []
        for i, step_template in enumerate(template["steps"], 1):
            step_id = f"step_{i}"

            # 根据步骤类型准备输入数据
            step_input = self._prepare_step_input(
                step_template["agent"],
                base_input,
                context
            )

            step = {
                "id": step_id,
                "agent_name": step_template["agent"],
                "description": step_template["description"],
                "input_data": step_input,
                "dependencies": [f"step_{i-1}"] if i > 1 else [],
                "estimated_time": step_template["estimated_time"]
            }
            steps.append(step)

        # 使用 LLM 优化计划
        try:
            optimized_plan = await self._optimize_plan_with_llm(
                template["name"],
                steps,
                intent_result
            )
            return optimized_plan
        except Exception:
            # 如果 LLM 优化失败，使用基础计划
            return {
                "workflow_name": template["name"],
                "total_steps": len(steps),
                "estimated_total_time": sum(s["estimated_time"] for s in steps),
                "steps": steps
            }

    def _prepare_step_input(
        self,
        agent_name: str,
        base_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """为特定Agent准备输入数据"""

        if agent_name == "requirement_analyzer":
            return {
                "raw_requirements": base_input["description"],
                "product_name": base_input["product_name"],
                "industry": base_input["industry"],
                "analysis_depth": "standard"
            }

        elif agent_name == "competitor_analyst":
            return {
                "product_name": base_input["product_name"],
                "industry": base_input["industry"],
                "keywords": base_input["key_features"]
            }

        elif agent_name == "prd_generator":
            return {
                "product_name": base_input["product_name"],
                "description": base_input["description"],
                "target_users": base_input["target_users"],
                "key_features": base_input["key_features"],
                "constraints": base_input["constraints"]
            }

        elif agent_name == "compliance_checker":
            return {
                "product_name": base_input["product_name"],
                "industry": base_input["industry"],
                "features": base_input["key_features"]
            }

        elif agent_name == "review_preparer":
            return {
                "product_name": base_input["product_name"],
                "document_type": "prd",
                "target_audience": "技术团队"
            }

        return base_input

    async def _optimize_plan_with_llm(
        self,
        workflow_name: str,
        steps: List[Dict],
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 LLM 优化任务计划"""

        prompt = f"""优化以下任务执行计划：

工作流名称: {workflow_name}

当前步骤:
{json.dumps(steps, ensure_ascii=False, indent=2)}

用户意图: {json.dumps(intent_result, ensure_ascii=False)}

请优化：
1. 调整步骤顺序（如果有依赖关系）
2. 调整预估时间
3. 添加必要的输入参数

输出优化后的 JSON 格式计划。"""

        response = await self._call_llm(
            prompt=prompt,
            system_prompt=self.SYSTEM_PROMPT
        )

        try:
            optimized = json.loads(response)
            return optimized
        except json.JSONDecodeError:
            # 返回原始计划
            return {
                "workflow_name": workflow_name,
                "total_steps": len(steps),
                "estimated_total_time": sum(s["estimated_time"] for s in steps),
                "steps": steps
            }

    def _validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """验证计划的有效性"""
        issues = []

        steps = plan.get("steps", [])

        # 检查循环依赖
        step_ids = {s["id"] for s in steps}
        for step in steps:
            for dep in step.get("dependencies", []):
                if dep not in step_ids:
                    issues.append(f"步骤 {step['id']} 依赖不存在的步骤 {dep}")

        # 检查Agent名称
        valid_agents = {
            "intent_classifier", "task_planner", "requirement_analyzer",
            "competitor_analyst", "prd_generator", "compliance_checker",
            "review_preparer"
        }
        for step in steps:
            if step.get("agent_name") not in valid_agents:
                issues.append(f"未知的 Agent: {step.get('agent_name')}")

        return {
            "status": "valid" if not issues else "invalid",
            "issues": issues,
            "step_count": len(steps),
            "estimated_time": plan.get("estimated_total_time", 0)
        }

    def get_execution_order(self, plan: Dict[str, Any]) -> List[List[str]]:
        """
        获取执行顺序（支持并行执行）

        Returns:
            按批次返回步骤ID，同批次可并行执行
        """
        steps = {s["id"]: s for s in plan.get("steps", [])}
        executed = set()
        batches = []

        while len(executed) < len(steps):
            batch = []
            for step_id, step in steps.items():
                if step_id in executed:
                    continue
                deps = step.get("dependencies", [])
                if all(d in executed for d in deps):
                    batch.append(step_id)

            if not batch:
                # 存在循环依赖
                raise ValueError("Circular dependency detected in plan")

            batches.append(batch)
            executed.update(batch)

        return batches
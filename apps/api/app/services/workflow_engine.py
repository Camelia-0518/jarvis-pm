"""
工作流引擎 - 支持多步骤技能编排
"""
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    skill_id: str
    step_name: str
    inputs_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None  # 条件表达式，如 "$.steps.step1.output.valid == true"
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 300  # 秒


@dataclass
class WorkflowStepResult:
    """工作流步骤执行结果"""
    step_name: str
    skill_id: str
    status: StepStatus
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "skill_id": self.skill_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.completed_at - self.started_at if self.completed_at and self.started_at else None
        }


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStep]
    version: str = "1.0"
    timeout: int = 1800  # 秒
    max_retries: int = 3


@dataclass
class WorkflowExecutionResult:
    """工作流执行结果"""
    workflow: str
    completed: bool
    results: List[WorkflowStepResult]
    outputs: Dict[str, Any]
    started_at: float
    completed_at: Optional[float]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow": self.workflow,
            "completed": self.completed,
            "results": [r.to_dict() for r in self.results],
            "outputs": self.outputs,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.completed_at - self.started_at if self.completed_at else None,
            "error": self.error
        }


# 预定义标准工作流
STANDARD_WORKFLOWS = {
    "product-design": WorkflowDefinition(
        name="product-design",
        description="产品设计完整流程：需求分析 → 商业模式 → PRD撰写",
        steps=[
            WorkflowStep(
                skill_id="requirement-analysis",
                step_name="需求分析",
                inputs_mapping={
                    "idea": "$.initial.idea",
                    "targetUsers": "$.initial.targetUsers",
                    "industry": "$.initial.industry",
                    "constraints": "$.initial.constraints"
                }
            ),
            WorkflowStep(
                skill_id="business-model",
                step_name="商业模式",
                inputs_mapping={
                    "productDescription": "$.steps.需求分析.output.productOneLiner",
                    "market": "$.initial.targetUsers",
                    "competitors": ""
                }
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="PRD文档",
                inputs_mapping={
                    "requirementAnalysis": "$.steps.需求分析.output.requirementDoc",
                    "template": "medical",
                    "detailLevel": "standard"
                },
                timeout=360  # PRD 生成耗时较长，单独放宽超时
            )
        ]
    ),
    "medical-product-review": WorkflowDefinition(
        name="medical-product-review",
        description="医疗产品评审流程",
        steps=[
            WorkflowStep(
                skill_id="compliance-check",
                step_name="合规检查",
                inputs_mapping={
                    "prdContent": "$.initial.prdContent",
                    "industry": "medical"
                }
            ),
            WorkflowStep(
                skill_id="ux-review",
                step_name="UX评审",
                inputs_mapping={
                    "prdContent": "$.initial.prdContent",
                    "userJourney": "$.initial.userJourney"
                },
                condition="$.steps.合规检查.output.compliant == true"
            )
        ]
    ),
    "quick-prd": WorkflowDefinition(
        name="quick-prd",
        description="快速PRD生成（单步骤）",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="快速PRD",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.idea",
                    "template": "medical",
                    "detailLevel": "standard"
                }
            )
        ]
    ),
    "medical-compliance-audit": WorkflowDefinition(
        name="medical-compliance-audit",
        description="医疗合规审计完整流程",
        steps=[
            WorkflowStep(
                skill_id="compliance-check",
                step_name="合规检查",
                inputs_mapping={
                    "prdContent": "$.initial.prdContent",
                    "industry": "medical"
                }
            ),
            WorkflowStep(
                skill_id="requirement-analysis",
                step_name="需求合规性分析",
                inputs_mapping={
                    "idea": "$.initial.idea",
                    "targetUsers": "患者和医护人员",
                    "industry": "medical",
                    "constraints": "必须符合医疗数据安全规范"
                }
            )
        ]
    )
}


class WorkflowEngine:
    """工作流引擎 - 执行多步骤技能编排"""

    def __init__(self, skill_executor: Optional[Callable] = None):
        self.skill_executor = skill_executor or self._default_skill_executor
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self._register_standard_workflows()

    def _register_standard_workflows(self):
        """注册标准工作流"""
        self.workflows.update(STANDARD_WORKFLOWS)

    def register_workflow(self, definition: WorkflowDefinition):
        """注册自定义工作流"""
        self.workflows[definition.name] = definition

    def _default_skill_executor(self, skill_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """默认技能执行器（用于测试）"""
        return {"status": "success", "skill": skill_id, "inputs": inputs}

    def _resolve_input_value(self, path: str, context: Dict[str, Any]) -> Any:
        """解析输入路径值

        支持的路径格式：
        - $.initial.xxx - 从初始输入获取
        - $.steps.xxx.output.yyy - 从步骤输出获取
        """
        if not path.startswith("$."):
            return path  # 直接返回静态值

        parts = path[2:].split(".")
        current = context

        try:
            for part in parts:
                if isinstance(current, dict):
                    current = current[part]
                else:
                    return None
            return current
        except (KeyError, TypeError):
            return None

    def _prepare_step_inputs(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备步骤输入参数"""
        inputs = {}
        for param, path in step.inputs_mapping.items():
            value = self._resolve_input_value(path, context)
            if value is not None:
                inputs[param] = value
        return inputs

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        if not condition:
            return True

        # 简单条件解析：$.steps.xxx.output.yyy == value
        try:
            if "==" in condition:
                left, right = condition.split("==", 1)
                left_val = self._resolve_input_value(left.strip(), context)
                right_val = right.strip().strip('"').strip("'")
                return str(left_val) == right_val
            elif "!=" in condition:
                left, right = condition.split("!=", 1)
                left_val = self._resolve_input_value(left.strip(), context)
                right_val = right.strip().strip('"').strip("'")
                return str(left_val) != right_val
        except Exception:
            pass

        return True  # 默认通过

    async def execute_workflow(
        self,
        workflow_name: str,
        initial_inputs: Dict[str, Any],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """执行工作流

        Args:
            workflow_name: 工作流名称
            initial_inputs: 初始输入参数
            stop_on_error: 遇到错误时是否停止

        Returns:
            工作流执行结果字典
        """
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            return {
                "workflow": workflow_name,
                "completed": False,
                "results": [],
                "outputs": {},
                "error": f"Workflow '{workflow_name}' not found",
                "started_at": time.time(),
                "completed_at": time.time()
            }

        started_at = time.time()
        context = {
            "initial": initial_inputs,
            "steps": {}
        }
        results: List[WorkflowStepResult] = []
        completed = True

        for step in workflow.steps:
            step_started = time.time()

            # 检查条件
            if step.condition and not self._evaluate_condition(step.condition, context):
                result = WorkflowStepResult(
                    step_name=step.step_name,
                    skill_id=step.skill_id,
                    status=StepStatus.SKIPPED,
                    started_at=step_started,
                    completed_at=time.time()
                )
                results.append(result)
                context["steps"][step.step_name] = {"output": {}}
                continue

            # 准备输入
            step_inputs = self._prepare_step_inputs(step, context)

            # 添加调试日志
            logger.debug(f"Executing skill {step.skill_id}")
            logger.debug(f"Inputs: {step_inputs}")

            try:
                # 执行技能
                output = await self._execute_skill_with_retry(
                    step.skill_id,
                    step_inputs,
                    step.timeout
                )

                result = WorkflowStepResult(
                    step_name=step.step_name,  # 使用 step_name 而不是 skill_id
                    skill_id=step.skill_id,
                    status=StepStatus.COMPLETED,
                    output=output if isinstance(output, dict) else {"result": output},
                    started_at=step_started,
                    completed_at=time.time()
                )
                context["steps"][step.step_name] = {"output": result.output}

            except Exception as e:
                result = WorkflowStepResult(
                    step_name=step.step_name,  # 使用 step_name 而不是 skill_id
                    skill_id=step.skill_id,
                    status=StepStatus.FAILED,
                    error=str(e),
                    started_at=step_started,
                    completed_at=time.time()
                )
                completed = False
                if stop_on_error:
                    results.append(result)
                    break

            results.append(result)

        completed_at = time.time()

        # 收集最终输出
        outputs = {}
        for result in results:
            if result.status == StepStatus.COMPLETED:
                outputs[result.step_name] = result.output

        execution_result = WorkflowExecutionResult(
            workflow=workflow_name,
            completed=completed and all(r.status == StepStatus.COMPLETED for r in results),
            results=results,
            outputs=outputs,
            started_at=started_at,
            completed_at=completed_at
        )

        return execution_result.to_dict()

    async def _execute_skill_with_retry(
        self,
        skill_id: str,
        inputs: Dict[str, Any],
        timeout: int,
        max_retries: int = 3
    ) -> Any:
        """带重试的技能执行"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await asyncio.wait_for(
                    self.skill_executor(skill_id, inputs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout}s"
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise Exception(f"Skill {skill_id} failed after {max_retries} attempts: {last_error}")

    async def execute_workflow_stream(
        self,
        workflow_name: str,
        initial_inputs: Dict[str, Any]
    ):
        """流式执行工作流（生成器）"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            yield {"type": "error", "message": f"Workflow '{workflow_name}' not found"}
            return

        context = {
            "initial": initial_inputs,
            "steps": {}
        }

        yield {"type": "start", "workflow": workflow_name, "total_steps": len(workflow.steps)}

        for i, step in enumerate(workflow.steps):
            yield {
                "type": "step_start",
                "step": i + 1,
                "total": len(workflow.steps),
                "step_name": step.step_name,
                "skill_id": step.skill_id
            }

            # 检查条件
            if step.condition and not self._evaluate_condition(step.condition, context):
                yield {"type": "step_skip", "step_name": step.step_name, "reason": "condition_not_met"}
                context["steps"][step.step_name] = {"output": {}}
                continue

            # 准备并执行
            step_inputs = self._prepare_step_inputs(step, context)

            try:
                output = await self._execute_skill_with_retry(
                    step.skill_id,
                    step_inputs,
                    step.timeout
                )

                context["steps"][step.step_name] = {"output": output if isinstance(output, dict) else {"result": output}}

                yield {
                    "type": "step_complete",
                    "step_name": step.step_name,
                    "output": context["steps"][step.step_name]
                }

            except Exception as e:
                yield {
                    "type": "step_error",
                    "step_name": step.step_name,
                    "error": str(e)
                }
                return

        yield {"type": "complete", "outputs": context["steps"]}

    def get_workflow_list(self) -> List[Dict[str, Any]]:
        """获取工作流列表"""
        return [
            {
                "name": wf.name,
                "description": wf.description,
                "version": wf.version,
                "steps_count": len(wf.steps)
            }
            for wf in self.workflows.values()
        ]

    def get_workflow_detail(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """获取工作流详情"""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            return None

        return {
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "timeout": workflow.timeout,
            "steps": [
                {
                    "step_name": step.step_name,
                    "skill_id": step.skill_id,
                    "inputs_mapping": step.inputs_mapping,
                    "condition": step.condition,
                    "depends_on": step.depends_on
                }
                for step in workflow.steps
            ]
        }

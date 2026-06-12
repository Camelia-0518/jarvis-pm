"""
工作流引擎 - 支持多步骤技能编排
"""
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class WorkflowStep:
    """工作流步骤定义"""
    skill_id: str
    step_name: str
    inputs_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[str] = None  # 条件表达式，如 "$.steps.step1.output.valid == true"
    depends_on: List[str] = field(default_factory=list)
    timeout: int = 300  # 秒
    on_timeout: Optional[str] = None  # 超时钩子标识
    on_retry_exhausted: Optional[str] = None  # 重试耗尽钩子标识
    sub_workflow: Optional[str] = None  # 子工作流名称（嵌套执行）


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


@dataclass(frozen=True)
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
                    "requirementAnalysis": "$.steps.需求分析.output.productOneLiner",
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
                    "prd": "$.initial.prdContent",
                    "complianceLevel": "level3"
                }
            ),
            WorkflowStep(
                skill_id="ux-design",
                step_name="UX评审",
                inputs_mapping={
                    "prd": "$.initial.prdContent",
                    "platform": "web",
                    "designStyle": "professional"
                },
                condition="$.steps.合规检查.output.overallStatus == pass"
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
    ),
    # ========== 技能链工作流（与前端 SKILL_CHAINS 对应）==========
    "full-delivery": WorkflowDefinition(
        name="full-delivery",
        description="完整交付方案：需求探索 → PRD撰写 → 交付计划 → 合规审查",
        steps=[
            WorkflowStep(
                skill_id="requirement-analysis",
                step_name="需求探索",
                inputs_mapping={
                    "idea": "$.initial.idea",
                    "targetUsers": "$.initial.targetUsers",
                    "industry": "$.initial.industry",
                    "constraints": "$.initial.constraints"
                }
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="PRD撰写",
                inputs_mapping={
                    "requirementAnalysis": "$.steps.需求探索.output.formatted_output",
                    "template": "$.initial.industry",
                    "detailLevel": "detailed"
                },
                depends_on=["需求探索"],
                timeout=360
            ),
            WorkflowStep(
                skill_id="milestone-plan",
                step_name="交付计划",
                inputs_mapping={
                    "prd": "$.steps.PRD撰写.output.markdown",
                    "teamSize": "$.initial.teamSize"
                },
                depends_on=["PRD撰写"]
            ),
            WorkflowStep(
                skill_id="compliance-check",
                step_name="合规审查",
                inputs_mapping={
                    "prd": "$.steps.PRD撰写.output.markdown",
                    "complianceLevel": "level3"
                },
                depends_on=["交付计划"]
            )
        ]
    ),
    "compliance-audit": WorkflowDefinition(
        name="compliance-audit",
        description="合规深度审查：合规检查 → 医疗评审 → 审查报告生成",
        steps=[
            WorkflowStep(
                skill_id="compliance-check",
                step_name="合规检查",
                inputs_mapping={
                    "prd": "$.initial.prdContent",
                    "complianceLevel": "$.initial.complianceLevel"
                }
            ),
            WorkflowStep(
                skill_id="medical-review",
                step_name="医疗评审",
                inputs_mapping={
                    "requirement": "$.initial.prdContent",
                    "featureType": "$.initial.featureType",
                    "patientData": "true"
                },
                depends_on=["合规检查"]
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="审查报告",
                inputs_mapping={
                    "requirementAnalysis": "$.steps.合规检查.output.formatted_output",
                    "template": "audit",
                    "detailLevel": "detailed"
                },
                depends_on=["医疗评审"],
                timeout=360
            )
        ]
    ),
    "requirement-discovery": WorkflowDefinition(
        name="requirement-discovery",
        description="需求探索：需求分析 → 商业模式 → 洞察报告生成",
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
                    "productDescription": "$.steps.需求分析.output.formatted_output",
                    "market": "$.initial.targetUsers",
                    "competitors": ""
                },
                depends_on=["需求分析"]
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="洞察报告",
                inputs_mapping={
                    "requirementAnalysis": "$.steps.需求分析.output.formatted_output",
                    "template": "discovery",
                    "detailLevel": "detailed"
                },
                depends_on=["商业模式"],
                timeout=360
            )
        ]
    ),
    "ai-model-prd": WorkflowDefinition(
        name="ai-model-prd",
        description="AI大模型产品PRD：覆盖模型能力、数据评估、提示词安全、反馈闭环、AI伦理",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="AI产品PRD",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "ai-model",
                    "detailLevel": "detailed"
                },
                timeout=360
            )
        ]
    ),
    "devops-prd": WorkflowDefinition(
        name="devops-prd",
        description="DevOps/内部工具PRD：覆盖自动化部署、监控告警、开发者体验、效率指标",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="DevOps工具PRD",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "devops",
                    "detailLevel": "detailed"
                },
                timeout=360
            )
        ]
    ),
    "project-kickoff": WorkflowDefinition(
        name="project-kickoff",
        description="项目启动包：需求分析 → 里程碑规划 → 项目章程，一套完整的项目启动文档",
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
                skill_id="milestone-plan",
                step_name="里程碑与风险",
                inputs_mapping={
                    "prd": "$.steps.需求分析.output.formatted_output",
                    "teamSize": "$.initial.teamSize"
                },
                depends_on=["需求分析"]
            ),
            WorkflowStep(
                skill_id="write-prd",
                step_name="项目章程",
                inputs_mapping={
                    "requirementAnalysis": "$.steps.需求分析.output.formatted_output",
                    "template": "project-charter",
                    "detailLevel": "detailed"
                },
                depends_on=["里程碑与风险"],
                timeout=360
            )
        ]
    ),
    "weekly-report": WorkflowDefinition(
        name="weekly-report",
        description="项目状态报告：基于本周工作内容生成专业的周报/日报",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="状态报告",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "status-report",
                    "detailLevel": "detailed"
                },
                timeout=360
            )
        ]
    ),
    "stakeholder-brief": WorkflowDefinition(
        name="stakeholder-brief",
        description="干系人沟通：按受众（客户/研发/交付/高层）生成定制化沟通简报",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="沟通简报",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "stakeholder-brief",
                    "detailLevel": "concise"
                },
                timeout=360
            )
        ]
    ),
    "delivery-playbook": WorkflowDefinition(
        name="delivery-playbook",
        description="标准化交付路径：将复杂业务抽象为可复用的交付方法论文档",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="交付路径手册",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "delivery-playbook",
                    "detailLevel": "detailed"
                },
                timeout=360
            )
        ]
    ),
    "retrospective": WorkflowDefinition(
        name="retrospective",
        description="项目复盘：生成结构化复盘报告和方法论沉淀",
        steps=[
            WorkflowStep(
                skill_id="write-prd",
                step_name="复盘报告",
                inputs_mapping={
                    "requirementAnalysis": "$.initial.requirementAnalysis",
                    "template": "retrospective",
                    "detailLevel": "detailed"
                },
                timeout=360
            )
        ]
    ),
}


class WorkflowEngine:
    """工作流引擎 - 执行多步骤技能编排"""

    def __init__(self, skill_executor: Optional[Callable] = None):
        self.skill_executor = skill_executor or self._default_skill_executor
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.hooks: Dict[str, Callable] = {}
        self._sub_workflow_depth: int = 0
        self._max_sub_workflow_depth: int = 3
        self._register_standard_workflows()

    def _register_standard_workflows(self):
        """注册标准工作流"""
        self.workflows.update(STANDARD_WORKFLOWS)

    def register_workflow(self, definition: WorkflowDefinition):
        """注册自定义工作流"""
        self.workflows[definition.name] = definition

    def register_hook(self, name: str, handler: Callable):
        """注册步骤钩子处理器

        Args:
            name: 钩子标识名称
            handler: 异步处理函数，接收 (step_name, skill_id, error, context) 参数
        """
        self.hooks[name] = handler

    @staticmethod
    def _detect_cycle(steps: List[WorkflowStep]) -> Optional[List[str]]:
        """Detect dependency cycles using DFS. Returns cycle path if found."""
        step_names = {s.step_name for s in steps}
        adj = {s.step_name: [d for d in s.depends_on if d in step_names] for s in steps}

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in step_names}
        parent = {}

        def dfs(node: str) -> Optional[List[str]]:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color[neighbor] == GRAY:
                    # Cycle detected - reconstruct path
                    cycle = [neighbor]
                    cur = node
                    while cur != neighbor:
                        cycle.append(cur)
                        cur = parent.get(cur, neighbor)
                    cycle.append(neighbor)
                    return list(reversed(cycle))
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for name in step_names:
            if color[name] == WHITE:
                cycle = dfs(name)
                if cycle:
                    return cycle
        return None

    async def _trigger_hook(
        self,
        hook_name: Optional[str],
        step_name: str,
        skill_id: str,
        error: str,
        context: Dict[str, Any]
    ):
        """触发步骤钩子"""
        if not hook_name or hook_name not in self.hooks:
            return
        try:
            handler = self.hooks[hook_name]
            await handler(step_name=step_name, skill_id=skill_id, error=error, context=context)
        except Exception:
            logger.exception("Hook %s failed for step %s", hook_name, step_name)

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
            else:
                logger.warning(
                    "Step '%s' input '%s': path '%s' resolved to None (missing in context)",
                    step.step_name, param, path
                )
        return inputs

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式

        支持的操作符:
        - ==, != : 相等/不等
        - >, <, >=, <= : 数值比较
        - in : 包含判断（如 \"pass\" in status）
        """
        if not condition:
            return True

        def _parse_value(val: str) -> Any:
            """解析条件值，支持数字、布尔、字符串"""
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            if val.startswith("'") and val.endswith("'"):
                return val[1:-1]
            if val.lower() == "true":
                return True
            if val.lower() == "false":
                return False
            if val.lower() == "none":
                return None
            try:
                if "." in val:
                    return float(val)
                return int(val)
            except ValueError:
                return val

        try:
            # 按优先级匹配操作符（长的先匹配避免冲突）
            for op in [">=", "<=", "!=", "==", ">", "<", " in "]:
                if op in condition:
                    if op == " in ":
                        left_str, right_str = condition.split(" in ", 1)
                        left_val = _parse_value(left_str)
                        right_val = self._resolve_input_value(right_str.strip(), context)
                        if isinstance(right_val, (list, tuple, str)):
                            return left_val in right_val
                        return False
                    else:
                        left_str, right_str = condition.split(op, 1)
                        left_val = self._resolve_input_value(left_str.strip(), context)
                        right_val = _parse_value(right_str)
                        if op == "==":
                            return left_val == right_val
                        elif op == "!=":
                            return left_val != right_val
                        elif op == ">":
                            return left_val is not None and right_val is not None and left_val > right_val
                        elif op == "<":
                            return left_val is not None and right_val is not None and left_val < right_val
                        elif op == ">=":
                            return left_val is not None and right_val is not None and left_val >= right_val
                        elif op == "<=":
                            return left_val is not None and right_val is not None and left_val <= right_val
            return True
        except Exception:
            logger.warning(f"Condition evaluation failed: {condition}")
            return True  # 默认通过

    async def execute_workflow(
        self,
        workflow_name: str,
        initial_inputs: Dict[str, Any],
        stop_on_error: bool = True
    ) -> Dict[str, Any]:
        """Execute workflow with DAG-based parallel step execution.

        Steps with no unresolved dependencies run in parallel via asyncio.gather.
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
        context = {"initial": initial_inputs, "steps": {}}
        results: Dict[str, WorkflowStepResult] = {}
        completed = True

        # Build step lookup and dependency tracking
        step_map = {s.step_name: s for s in workflow.steps}
        pending = set(s.step_name for s in workflow.steps)
        failed_steps: set[str] = set()

        # Detect cycles before execution
        cycle = self._detect_cycle(workflow.steps)
        if cycle:
            return {
                "workflow": workflow_name,
                "completed": False,
                "results": [],
                "outputs": {},
                "error": f"Cycle detected in workflow dependencies: {' -> '.join(cycle)}",
                "started_at": started_at,
                "completed_at": time.time()
            }

        async def _run_single_step(step: WorkflowStep) -> WorkflowStepResult:
            """Execute a single step and return result."""
            step_started = time.time()

            # Evaluate condition
            if step.condition and not self._evaluate_condition(step.condition, context):
                return WorkflowStepResult(
                    step_name=step.step_name,
                    skill_id=step.skill_id,
                    status=StepStatus.SKIPPED,
                    started_at=step_started,
                    completed_at=time.time()
                )

            step_inputs = self._prepare_step_inputs(step, context)
            logger.debug("Executing skill %s (step: %s)", step.skill_id, step.step_name)

            try:
                if step.sub_workflow:
                    if self._sub_workflow_depth >= self._max_sub_workflow_depth:
                        raise Exception(f"Sub-workflow depth exceeded ({self._max_sub_workflow_depth})")
                    self._sub_workflow_depth += 1
                    try:
                        sub_result = await self.execute_workflow(
                            step.sub_workflow,
                            {**initial_inputs, **step_inputs},
                            stop_on_error=stop_on_error
                        )
                        output = sub_result
                    finally:
                        self._sub_workflow_depth -= 1
                else:
                    output = await self._execute_skill_with_retry(
                        step.skill_id,
                        step_inputs,
                        step.timeout,
                        max_retries=workflow.max_retries,
                        step=step,
                        context=context,
                    )

                return WorkflowStepResult(
                    step_name=step.step_name,
                    skill_id=step.skill_id,
                    status=StepStatus.COMPLETED,
                    output=output if isinstance(output, dict) else {"result": output},
                    started_at=step_started,
                    completed_at=time.time()
                )
            except Exception as e:
                return WorkflowStepResult(
                    step_name=step.step_name,
                    skill_id=step.skill_id,
                    status=StepStatus.FAILED,
                    error=str(e),
                    started_at=step_started,
                    completed_at=time.time()
                )

        # Main execution loop: run ready steps in parallel batches
        while pending:
            # Find steps whose dependencies are all satisfied
            ready = []
            for name in list(pending):
                step = step_map[name]
                deps_satisfied = all(
                    dep in results and results[dep].status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                    for dep in step.depends_on
                )
                if deps_satisfied:
                    ready.append(step)

            if not ready:
                # Deadlock: remaining pending steps have unmet dependencies
                break

            # Execute ready steps in parallel
            batch_results = await asyncio.gather(*[_run_single_step(s) for s in ready])

            for result in batch_results:
                results[result.step_name] = result
                pending.discard(result.step_name)

                if result.status == StepStatus.COMPLETED:
                    context["steps"][result.step_name] = {"output": result.output}
                elif result.status == StepStatus.SKIPPED:
                    context["steps"][result.step_name] = {"output": {}}
                elif result.status == StepStatus.FAILED:
                    failed_steps.add(result.step_name)
                    completed = False
                    if stop_on_error:
                        pending.clear()
                        break

        completed_at = time.time()

        # Build ordered results list matching original step order
        ordered_results = [results[s.step_name] for s in workflow.steps if s.step_name in results]

        # Collect outputs from completed steps only
        outputs = {
            r.step_name: r.output
            for r in ordered_results
            if r.status == StepStatus.COMPLETED
        }

        execution_result = WorkflowExecutionResult(
            workflow=workflow_name,
            completed=completed and len(failed_steps) == 0 and len(pending) == 0,
            results=ordered_results,
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
        max_retries: int = 3,
        step: Optional[WorkflowStep] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """带重试的技能执行"""
        last_error = None
        step_name = step.step_name if step else skill_id
        hook_context = context or {}

        for attempt in range(max_retries):
            try:
                return await asyncio.wait_for(
                    self.skill_executor(skill_id, inputs),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                last_error = f"Timeout after {timeout}s"
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 30))  # 指数退避，上限30s
                else:
                    # 重试耗尽且为超时
                    if step and step.on_timeout:
                        await self._trigger_hook(
                            step.on_timeout, step_name, skill_id, last_error, hook_context
                        )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 30))

        # 重试全部耗尽
        if step and step.on_retry_exhausted:
            await self._trigger_hook(
                step.on_retry_exhausted, step_name, skill_id, last_error, hook_context
            )

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
                    step.timeout,
                    max_retries=workflow.max_retries,
                    step=step,
                    context=context,
                )

                context["steps"][step.step_name] = {"output": output if isinstance(output, dict) else {"result": output}}

                yield {
                    "type": "step_complete",
                    "step_name": step.step_name,
                    "skill_id": step.skill_id,
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
                    "depends_on": step.depends_on,
                    "timeout": step.timeout,
                    "on_timeout": step.on_timeout,
                    "on_retry_exhausted": step.on_retry_exhausted,
                    "sub_workflow": step.sub_workflow,
                }
                for step in workflow.steps
            ]
        }
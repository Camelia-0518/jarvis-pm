# Agent 系统实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建以 Kimi Coding API 为核心的 Agent 执行系统，实现自动任务编排、工具调用和记忆管理

**Architecture:** 采用分层架构（API -> Strategy -> Tactical -> Execution -> Memory），使用 Redis 作为任务队列，支持 50+ Agent 动态加载

**Tech Stack:** FastAPI, Redis, PostgreSQL, Kimi Coding API, Pydantic

---

## 准备工作

### Task 0: 确认环境

**Files:**
- Check: `apps/api/requirements.txt`
- Check: `apps/api/app/main.py`
- Check: `docker-compose.yml`

**Step 1: 验证现有后端可运行**

```bash
cd C:/Users/13400/.claude/projects/jarvis-pm/apps/api
source venv/Scripts/activate  # Windows: venv\Scripts\activate
python -c "import app.main; print('OK')"
```

Expected: `OK`

**Step 2: 检查 Redis 配置**

```python
# 在 apps/api/app/core/config.py 中确认
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

**Step 3: 安装新依赖**

```bash
pip install redis rq httpx pydantic-settings
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: prepare agent system dependencies"
```

---

## 第一阶段：Agent 核心框架

### Task 1: 创建 Agent 基础类

**Files:**
- Create: `apps/api/app/agents/__init__.py`
- Create: `apps/api/app/agents/base.py`
- Test: `apps/api/tests/agents/test_base.py`

**Step 1: 创建 Agent 目录结构**

```bash
mkdir -p apps/api/app/agents/{agents,tools,engine}
mkdir -p apps/api/tests/agents
```

**Step 2: 编写基础 Agent 类**

```python
# apps/api/app/agents/base.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid


class AgentConfig(BaseModel):
    """Agent 配置模型"""
    id: str
    name: str
    description: str
    system_prompt: str
    tools: List[str] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    triggers: List[str] = []
    next_agents: List[str] = []


class AgentExecutionResult(BaseModel):
    """Agent 执行结果"""
    agent_id: str
    task_id: str
    input: Dict[str, Any]
    output: str
    tools_used: List[Dict[str, Any]] = []
    execution_time: float
    timestamp: datetime
    status: str  # "success", "failed", "retrying"


class BaseAgent:
    """Agent 基类 - 所有 Agent 继承此类"""
    
    def __init__(self, config: AgentConfig, llm_client=None, tool_registry=None):
        self.config = config
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.execution_history: List[AgentExecutionResult] = []
    
    async def execute(self, task_input: Dict[str, Any], context: Dict[str, Any] = None) -> AgentExecutionResult:
        """执行 Agent 任务 - 子类可重写"""
        task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # 1. 准备 Prompt
            messages = self._prepare_messages(task_input, context)
            
            # 2. 调用 LLM
            response = await self._call_llm(messages)
            
            # 3. 处理工具调用
            tools_used = []
            if self._has_tool_calls(response):
                tool_results = await self._execute_tools(response)
                tools_used = tool_results
                # 再次调用获取最终结果
                messages.extend(self._format_tool_results(tool_results))
                response = await self._call_llm(messages)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = AgentExecutionResult(
                agent_id=self.config.id,
                task_id=task_id,
                input=task_input,
                output=response,
                tools_used=tools_used,
                execution_time=execution_time,
                timestamp=datetime.now(),
                status="success"
            )
            
            self.execution_history.append(result)
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return AgentExecutionResult(
                agent_id=self.config.id,
                task_id=task_id,
                input=task_input,
                output=f"Error: {str(e)}",
                tools_used=[],
                execution_time=execution_time,
                timestamp=datetime.now(),
                status="failed"
            )
    
    def _prepare_messages(self, task_input: Dict[str, Any], context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """准备 LLM 消息"""
        messages = [{"role": "system", "content": self.config.system_prompt}]
        
        user_content = f"任务输入: {task_input}"
        if context:
            user_content += f"\n上下文: {context}"
        
        messages.append({"role": "user", "content": user_content})
        return messages
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM - 由子类或外部注入实现"""
        if not self.llm_client:
            raise NotImplementedError("LLM client not provided")
        return await self.llm_client.chat(messages)
    
    def _has_tool_calls(self, response: str) -> bool:
        """检查响应是否包含工具调用"""
        # 简单实现：检查是否包含 TOOL: 前缀
        return "TOOL:" in response
    
    async def _execute_tools(self, response: str) -> List[Dict[str, Any]]:
        """执行工具调用"""
        if not self.tool_registry:
            return []
        
        # 解析工具调用
        tools_used = []
        # TODO: 实现工具调用解析
        return tools_used
    
    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """格式化工具结果为消息"""
        return [{"role": "user", "content": f"工具结果: {result}"} for result in tool_results]


# Agent 注册表
class AgentRegistry:
    """Agent 注册表 - 管理所有 Agent"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent):
        """注册 Agent"""
        self._agents[agent.config.id] = agent
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[AgentConfig]:
        """列出所有 Agent 配置"""
        return [agent.config for agent in self._agents.values()]
    
    def find_by_trigger(self, intent: str) -> List[BaseAgent]:
        """根据意图查找匹配的 Agent"""
        matched = []
        for agent in self._agents.values():
            if any(trigger in intent.lower() for trigger in agent.config.triggers):
                matched.append(agent)
        return matched


# 全局注册表实例
agent_registry = AgentRegistry()
```

**Step 3: 编写测试**

```python
# apps/api/tests/agents/test_base.py
import pytest
from app.agents.base import BaseAgent, AgentConfig, AgentRegistry


@pytest.fixture
def sample_config():
    return AgentConfig(
        id="test-agent",
        name="Test Agent",
        description="For testing",
        system_prompt="You are a test agent.",
        tools=[],
        triggers=["test"]
    )


def test_agent_config_creation(sample_config):
    assert sample_config.id == "test-agent"
    assert sample_config.name == "Test Agent"


def test_agent_registry_register(sample_config):
    registry = AgentRegistry()
    agent = BaseAgent(sample_config)
    
    registry.register(agent)
    
    assert registry.get("test-agent") == agent
    assert len(registry.list_agents()) == 1


def test_agent_registry_find_by_trigger(sample_config):
    registry = AgentRegistry()
    agent = BaseAgent(sample_config)
    registry.register(agent)
    
    matched = registry.find_by_trigger("this is a test intent")
    
    assert len(matched) == 1
    assert matched[0].config.id == "test-agent"


@pytest.mark.asyncio
async def test_agent_execute_without_llm(sample_config):
    agent = BaseAgent(sample_config)
    
    with pytest.raises(NotImplementedError):
        await agent.execute({"query": "test"})
```

**Step 4: 运行测试**

```bash
cd C:/Users/13400/.claude/projects/jarvis-pm/apps/api
pytest tests/agents/test_base.py -v
```

Expected: 
- `test_agent_config_creation` PASS
- `test_agent_registry_register` PASS
- `test_agent_registry_find_by_trigger` PASS
- `test_agent_execute_without_llm` PASS

**Step 5: Commit**

```bash
git add apps/api/app/agents/ apps/api/tests/agents/
git commit -m "feat: add Agent base class and registry"
```

---

### Task 2: 实现 Kimi Coding API 客户端

**Files:**
- Create: `apps/api/app/agents/llm_client.py`
- Modify: `apps/api/app/core/config.py`
- Test: `apps/api/tests/agents/test_llm_client.py`

**Step 1: 添加 Kimi API 配置**

```python
# apps/api/app/core/config.py (添加)
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # Kimi Coding API
    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.kimi.com/coding"
    KIMI_MODEL: str = "kimi-k2.5"
    KIMI_TIMEOUT: int = 60
```

**Step 2: 实现 LLM 客户端**

```python
# apps/api/app/agents/llm_client.py
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
import json


class LLMClient:
    """LLM 客户端基类"""
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        raise NotImplementedError


class KimiCodingClient(LLMClient):
    """Kimi Coding API 客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.KIMI_API_KEY
        self.base_url = base_url or settings.KIMI_BASE_URL
        self.model = model or settings.KIMI_MODEL
        self.timeout = settings.KIMI_TIMEOUT
    
    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: List[str] = None
    ) -> str:
        """调用 Kimi Coding API"""
        
        if not self.api_key:
            raise ValueError("KIMI_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            payload["tools"] = tools
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"Kimi API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        """流式调用 Kimi API"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except:
                            pass


class LLMClientFactory:
    """LLM 客户端工厂"""
    
    @staticmethod
    def create(provider: str = "kimi") -> LLMClient:
        if provider == "kimi":
            return KimiCodingClient()
        raise ValueError(f"Unknown provider: {provider}")
```

**Step 3: 编写测试（Mock 版本）**

```python
# apps/api/tests/agents/test_llm_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.llm_client import KimiCodingClient


@pytest.mark.asyncio
async def test_kimi_client_chat_success():
    client = KimiCodingClient(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello, world!"}}]
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await client.chat([{"role": "user", "content": "Hi"}])
        
        assert result == "Hello, world!"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_kimi_client_chat_no_api_key():
    client = KimiCodingClient(api_key="")
    
    with pytest.raises(ValueError, match="KIMI_API_KEY not configured"):
        await client.chat([{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_kimi_client_chat_api_error():
    client = KimiCodingClient(api_key="test-key")
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception, match="Kimi API error"):
            await client.chat([{"role": "user", "content": "Hi"}])
```

**Step 4: 运行测试**

```bash
pytest tests/agents/test_llm_client.py -v
```

Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Kimi Coding API client"
```

---

### Task 3: 实现 IntentClassifier Agent

**Files:**
- Create: `apps/api/app/agents/agents/intent_classifier.py`
- Test: `apps/api/tests/agents/test_intent_classifier.py`

**Step 1: 实现 IntentClassifier**

```python
# apps/api/app/agents/agents/intent_classifier.py
import json
from typing import Dict, Any
from app.agents.base import BaseAgent, AgentConfig, AgentExecutionResult


INTENT_CLASSIFIER_CONFIG = AgentConfig(
    id="intent-classifier",
    name="Intent Classifier",
    description="识别用户意图，分类任务类型",
    system_prompt="""你是一位专业的意图识别专家。分析用户的输入，识别：

1. 主要意图（intent）：用户的需求是什么
   - requirement_analysis: 需求分析
   - competitor_analysis: 竞品分析
   - prd_writing: PRD撰写
   - compliance_check: 合规检查
   - review_preparation: 评审准备
   - general_chat: 闲聊/咨询

2. 关键实体（entities）：提取产品名、功能点等

3. 置信度（confidence）：0-1之间的数值

请以JSON格式返回：
{
    "intent": "requirement_analysis",
    "entities": {"product": "切片借阅平台"},
    "confidence": 0.95,
    "reasoning": "用户提到'做'和'分析需求'，属于需求分析类任务"
}""",
    triggers=["分析", "写", "检查", "准备", "帮"],
)


class IntentClassifierAgent(BaseAgent):
    """意图分类 Agent"""
    
    def __init__(self, llm_client=None):
        super().__init__(INTENT_CLASSIFIER_CONFIG, llm_client)
    
    async def execute(self, task_input: Dict[str, Any], context: Dict[str, Any] = None) -> AgentExecutionResult:
        """执行意图分类"""
        result = await super().execute(task_input, context)
        
        # 解析输出为结构化数据
        if result.status == "success":
            try:
                parsed = json.loads(result.output)
                result.output = json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                # 如果 LLM 没有返回有效 JSON，标记为需要重试
                result.status = "retrying"
                result.output = f"Failed to parse: {result.output}"
        
        return result
    
    def parse_result(self, result: AgentExecutionResult) -> Dict[str, Any]:
        """解析执行结果为字典"""
        try:
            return json.loads(result.output)
        except:
            return {
                "intent": "general_chat",
                "entities": {},
                "confidence": 0.0,
                "reasoning": "解析失败"
            }
```

**Step 2: 编写测试**

```python
# apps/api/tests/agents/test_intent_classifier.py
import pytest
import json
from unittest.mock import AsyncMock
from app.agents.agents.intent_classifier import IntentClassifierAgent


@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.chat.return_value = json.dumps({
        "intent": "requirement_analysis",
        "entities": {"product": "切片借阅平台"},
        "confidence": 0.95,
        "reasoning": "用户需要分析需求"
    })
    return client


@pytest.mark.asyncio
async def test_intent_classifier_success(mock_llm_client):
    agent = IntentClassifierAgent(llm_client=mock_llm_client)
    
    result = await agent.execute({"query": "我要做切片借阅平台，帮我分析需求"})
    
    assert result.status == "success"
    assert result.agent_id == "intent-classifier"
    
    parsed = agent.parse_result(result)
    assert parsed["intent"] == "requirement_analysis"
    assert parsed["entities"]["product"] == "切片借阅平台"


@pytest.mark.asyncio
async def test_intent_classifier_invalid_json(mock_llm_client):
    mock_llm_client.chat.return_value = "This is not JSON"
    
    agent = IntentClassifierAgent(llm_client=mock_llm_client)
    result = await agent.execute({"query": "test"})
    
    assert result.status == "retrying"
```

**Step 3: 运行测试**

```bash
pytest tests/agents/test_intent_classifier.py -v
```

Expected: 2 tests PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add IntentClassifier agent"
```

---

## 第二阶段：任务编排和队列系统

### Task 4: 实现任务规划器（TaskPlanner）

**Files:**
- Create: `apps/api/app/agents/engine/task_planner.py`
- Test: `apps/api/tests/agents/test_task_planner.py`

**Step 1: 实现 TaskPlanner**

```python
# apps/api/app/agents/engine/task_planner.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json


class TaskStep(BaseModel):
    """任务步骤"""
    step_id: str
    agent_id: str
    task_description: str
    input_data: Dict[str, Any]
    dependencies: List[str] = []  # 依赖的步骤ID
    status: str = "pending"  # pending, running, completed, failed


class TaskPlan(BaseModel):
    """任务执行计划"""
    plan_id: str
    user_input: str
    intent: Dict[str, Any]
    steps: List[TaskStep]
    created_at: str


class TaskPlanner:
    """任务规划器 - 将意图分解为可执行的任务链"""
    
    AGENT_WORKFLOWS = {
        "requirement_analysis": [
            {"agent": "intent-classifier", "desc": "确认意图"},
            {"agent": "requirement-analyst", "desc": "分析需求"},
            {"agent": "prd-writer", "desc": "生成PRD初稿"},
        ],
        "competitor_analysis": [
            {"agent": "intent-classifier", "desc": "确认意图"},
            {"agent": "competitor-analyst", "desc": "竞品分析"},
        ],
        "prd_writing": [
            {"agent": "intent-classifier", "desc": "确认意图"},
            {"agent": "requirement-analyst", "desc": "需求分析"},
            {"agent": "competitor-analyst", "desc": "竞品分析"},
            {"agent": "prd-writer", "desc": "撰写PRD"},
            {"agent": "compliance-checker", "desc": "合规检查"},
        ],
    }
    
    def create_plan(self, user_input: str, intent_result: Dict[str, Any]) -> TaskPlan:
        """创建任务计划"""
        import uuid
        from datetime import datetime
        
        intent = intent_result.get("intent", "general_chat")
        entities = intent_result.get("entities", {})
        
        plan_id = str(uuid.uuid4())
        steps = []
        
        # 获取工作流
        workflow = self.AGENT_WORKFLOWS.get(intent, [])
        
        # 构建任务步骤
        prev_step_id = None
        for i, wf_step in enumerate(workflow):
            step_id = f"{plan_id}-{i}"
            
            step = TaskStep(
                step_id=step_id,
                agent_id=wf_step["agent"],
                task_description=wf_step["desc"],
                input_data={
                    "user_input": user_input,
                    "entities": entities,
                    "intent": intent,
                },
                dependencies=[prev_step_id] if prev_step_id else []
            )
            steps.append(step)
            prev_step_id = step_id
        
        return TaskPlan(
            plan_id=plan_id,
            user_input=user_input,
            intent=intent_result,
            steps=steps,
            created_at=datetime.now().isoformat()
        )
    
    def get_next_executable_steps(self, plan: TaskPlan) -> List[TaskStep]:
        """获取当前可执行的步骤（依赖已完成）"""
        executable = []
        completed_steps = {s.step_id for s in plan.steps if s.status == "completed"}
        
        for step in plan.steps:
            if step.status == "pending":
                # 检查依赖是否全部完成
                if all(dep in completed_steps for dep in step.dependencies):
                    executable.append(step)
        
        return executable
```

**Step 2: 编写测试**

```python
# apps/api/tests/agents/test_task_planner.py
import pytest
from app.agents.engine.task_planner import TaskPlanner, TaskPlan


@pytest.fixture
def planner():
    return TaskPlanner()


def test_create_plan_requirement_analysis(planner):
    intent_result = {
        "intent": "requirement_analysis",
        "entities": {"product": "切片借阅平台"},
        "confidence": 0.95
    }
    
    plan = planner.create_plan("我要做切片借阅平台", intent_result)
    
    assert plan.plan_id is not None
    assert plan.user_input == "我要做切片借阅平台"
    assert len(plan.steps) == 3
    assert plan.steps[0].agent_id == "intent-classifier"
    assert plan.steps[1].agent_id == "requirement-analyst"


def test_get_next_executable_steps(planner):
    intent_result = {"intent": "requirement_analysis", "entities": {}}
    plan = planner.create_plan("test", intent_result)
    
    # 初始状态，第一个步骤可执行
    executable = planner.get_next_executable_steps(plan)
    assert len(executable) == 1
    assert executable[0].agent_id == "intent-classifier"
    
    # 标记第一个步骤完成
    plan.steps[0].status = "completed"
    
    # 第二个步骤现在可执行
    executable = planner.get_next_executable_steps(plan)
    assert len(executable) == 1
    assert executable[0].agent_id == "requirement-analyst"
```

**Step 3: 运行测试**

```bash
pytest tests/agents/test_task_planner.py -v
```

Expected: 2 tests PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add TaskPlanner for workflow orchestration"
```

---

### Task 5: 实现任务队列（Redis + RQ）

**Files:**
- Create: `apps/api/app/agents/engine/task_queue.py`
- Modify: `docker-compose.yml`
- Test: `apps/api/tests/agents/test_task_queue.py`

**Step 1: 确保 Redis 服务可用**

```yaml
# docker-compose.yml 添加（如果不存在）
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    
  # ... 其他服务 ...

volumes:
  redis_data:
```

**Step 2: 实现任务队列**

```python
# apps/api/app/agents/engine/task_queue.py
import json
import redis
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings


class TaskQueue:
    """Redis 任务队列 - 管理 Agent 任务"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
        # 队列名称
        self.task_queue = "agent:tasks:pending"
        self.task_processing = "agent:tasks:processing"
        self.task_completed = "agent:tasks:completed"
        self.task_failed = "agent:tasks:failed"
    
    def enqueue(self, task: Dict[str, Any]) -> str:
        """将任务加入队列"""
        task_id = task.get("task_id")
        task["enqueued_at"] = datetime.now().isoformat()
        task["status"] = "pending"
        
        self.redis_client.lpush(self.task_queue, json.dumps(task))
        return task_id
    
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """从队列取出一个任务"""
        # 使用 brpop 阻塞等待
        result = self.redis_client.brpop(self.task_queue, timeout=1)
        if result:
            _, task_json = result
            task = json.loads(task_json)
            task["started_at"] = datetime.now().isoformat()
            task["status"] = "processing"
            
            # 加入处理中集合
            self.redis_client.hset(self.task_processing, task["task_id"], json.dumps(task))
            return task
        return None
    
    def complete(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成"""
        # 从处理中移除
        task_json = self.redis_client.hget(self.task_processing, task_id)
        if task_json:
            task = json.loads(task_json)
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            task["result"] = result
            
            # 加入已完成集合
            self.redis_client.hset(self.task_completed, task_id, json.dumps(task))
            self.redis_client.hdel(self.task_processing, task_id)
    
    def fail(self, task_id: str, error: str):
        """标记任务失败"""
        task_json = self.redis_client.hget(self.task_processing, task_id)
        if task_json:
            task = json.loads(task_json)
            task["status"] = "failed"
            task["failed_at"] = datetime.now().isoformat()
            task["error"] = error
            
            self.redis_client.hset(self.task_failed, task_id, json.dumps(task))
            self.redis_client.hdel(self.task_processing, task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 依次检查各个集合
        for collection in [self.task_processing, self.task_completed, self.task_failed]:
            task_json = self.redis_client.hget(collection, task_id)
            if task_json:
                return json.loads(task_json)
        return None
    
    def get_queue_length(self) -> int:
        """获取队列长度"""
        return self.redis_client.llen(self.task_queue)


# 全局任务队列实例
task_queue = TaskQueue()
```

**Step 3: 编写测试**

```python
# apps/api/tests/agents/test_task_queue.py
import pytest
import json
from unittest.mock import MagicMock, patch
from app.agents.engine.task_queue import TaskQueue


@pytest.fixture
def mock_redis():
    with patch('app.agents.engine.task_queue.redis.from_url') as mock:
        redis_client = MagicMock()
        mock.return_value = redis_client
        yield redis_client


def test_enqueue(mock_redis):
    queue = TaskQueue("redis://localhost")
    
    task = {"task_id": "test-1", "agent_id": "intent-classifier"}
    task_id = queue.enqueue(task)
    
    assert task_id == "test-1"
    mock_redis.lpush.assert_called_once()


def test_dequeue(mock_redis):
    queue = TaskQueue("redis://localhost")
    
    mock_redis.brpop.return_value = ("queue", json.dumps({"task_id": "test-1"}))
    
    task = queue.dequeue()
    
    assert task is not None
    assert task["task_id"] == "test-1"
    assert task["status"] == "processing"


def test_complete(mock_redis):
    queue = TaskQueue("redis://localhost")
    
    queue.complete("test-1", {"output": "success"})
    
    mock_redis.hset.assert_called()
    mock_redis.hdel.assert_called_with("agent:tasks:processing", "test-1")
```

**Step 4: 运行测试**

```bash
pytest tests/agents/test_task_queue.py -v
```

Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Redis task queue for agent execution"
```

---

## 第三阶段：执行引擎和 API

### Task 6: 实现 Agent 执行引擎

**Files:**
- Create: `apps/api/app/agents/engine/executor.py`
- Test: `apps/api/tests/agents/test_executor.py`

**Step 1: 实现执行引擎**

```python
# apps/api/app/agents/engine/executor.py
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.agents.base import agent_registry, BaseAgent
from app.agents.engine.task_planner import TaskPlanner, TaskPlan, TaskStep
from app.agents.engine.task_queue import TaskQueue, task_queue
from app.agents.llm_client import LLMClientFactory
from app.agents.agents.intent_classifier import IntentClassifierAgent


class AgentExecutor:
    """Agent 执行引擎 - 核心调度器"""
    
    def __init__(self):
        self.task_planner = TaskPlanner()
        self.task_queue = task_queue
        self.llm_client = LLMClientFactory.create("kimi")
        self._register_agents()
    
    def _register_agents(self):
        """注册所有 Agent"""
        # 注册 IntentClassifier
        intent_agent = IntentClassifierAgent(llm_client=self.llm_client)
        agent_registry.register(intent_agent)
        
        # TODO: 注册其他 Agent
    
    async def execute_user_request(
        self, 
        user_input: str, 
        session_id: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行用户请求 - 完整流程"""
        
        session_id = session_id or str(uuid.uuid4())
        
        # 1. 意图识别
        intent_agent = agent_registry.get("intent-classifier")
        intent_result = await intent_agent.execute(
            {"query": user_input},
            context
        )
        
        if intent_result.status != "success":
            return {
                "session_id": session_id,
                "status": "failed",
                "error": "Intent classification failed",
                "details": intent_result.output
            }
        
        parsed_intent = intent_agent.parse_result(intent_result)
        
        # 2. 任务规划
        plan = self.task_planner.create_plan(user_input, parsed_intent)
        
        # 3. 将任务加入队列
        for step in plan.steps:
            task = {
                "task_id": step.step_id,
                "plan_id": plan.plan_id,
                "session_id": session_id,
                "agent_id": step.agent_id,
                "input": step.input_data,
                "dependencies": step.dependencies
            }
            self.task_queue.enqueue(task)
        
        return {
            "session_id": session_id,
            "plan_id": plan.plan_id,
            "status": "queued",
            "intent": parsed_intent,
            "total_steps": len(plan.steps),
            "message": "任务已入队，开始执行"
        }
    
    async def execute_plan(self, plan: TaskPlan):
        """执行完整计划"""
        results = []
        
        while True:
            # 获取可执行的步骤
            executable_steps = self.task_planner.get_next_executable_steps(plan)
            
            if not executable_steps:
                # 检查是否全部完成
                all_completed = all(s.status in ["completed", "failed"] for s in plan.steps)
                if all_completed:
                    break
                # 等待或重试
                await asyncio.sleep(0.5)
                continue
            
            # 并行执行可执行的步骤
            tasks = [self._execute_step(step) for step in executable_steps]
            step_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 更新步骤状态
            for step, result in zip(executable_steps, step_results):
                if isinstance(result, Exception):
                    step.status = "failed"
                else:
                    step.status = "completed"
                    results.append(result)
        
        return results
    
    async def _execute_step(self, step: TaskStep) -> Dict[str, Any]:
        """执行单个步骤"""
        agent = agent_registry.get(step.agent_id)
        
        if not agent:
            raise ValueError(f"Agent not found: {step.agent_id}")
        
        # 设置 LLM 客户端
        if not agent.llm_client:
            agent.llm_client = self.llm_client
        
        result = await agent.execute(step.input_data)
        
        # 更新任务状态
        if result.status == "success":
            self.task_queue.complete(step.step_id, {"output": result.output})
        else:
            self.task_queue.fail(step.step_id, result.output)
        
        return {
            "step_id": step.step_id,
            "agent_id": step.agent_id,
            "result": result
        }
    
    async def process_queue(self):
        """后台任务：处理队列中的任务"""
        while True:
            task = self.task_queue.dequeue()
            
            if task:
                try:
                    agent = agent_registry.get(task["agent_id"])
                    if agent:
                        result = await agent.execute(task["input"])
                        self.task_queue.complete(task["task_id"], {"output": result.output})
                except Exception as e:
                    self.task_queue.fail(task["task_id"], str(e))
            else:
                # 队列为空，等待
                await asyncio.sleep(1)


# 全局执行器实例
agent_executor = AgentExecutor()
```

**Step 2: 编写测试**

```python
# apps/api/tests/agents/test_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.engine.executor import AgentExecutor


@pytest.fixture
def mock_agent_registry():
    with patch('app.agents.engine.executor.agent_registry') as mock:
        yield mock


@pytest.fixture
def mock_task_queue():
    with patch('app.agents.engine.executor.task_queue') as mock:
        yield mock


@pytest.mark.asyncio
async def test_execute_user_request(mock_agent_registry, mock_task_queue):
    # Mock IntentClassifier
    mock_intent_agent = AsyncMock()
    mock_intent_agent.execute.return_value = MagicMock(
        status="success",
        output='{"intent": "requirement_analysis", "entities": {}}'
    )
    mock_intent_agent.parse_result.return_value = {
        "intent": "requirement_analysis",
        "entities": {}
    }
    mock_agent_registry.get.return_value = mock_intent_agent
    
    executor = AgentExecutor()
    executor._register_agents = lambda: None  # 跳过注册
    
    result = await executor.execute_user_request("我要做切片借阅平台")
    
    assert result["status"] == "queued"
    assert result["total_steps"] == 3  # requirement_analysis 工作流有3步
    mock_task_queue.enqueue.assert_called()


@pytest.mark.asyncio
async def test_execute_step_success(mock_agent_registry):
    mock_agent = AsyncMock()
    mock_agent.execute.return_value = MagicMock(
        status="success",
        output="Test output"
    )
    mock_agent_registry.get.return_value = mock_agent
    
    executor = AgentExecutor()
    
    from app.agents.engine.task_planner import TaskStep
    step = TaskStep(
        step_id="test-1",
        agent_id="test-agent",
        task_description="Test",
        input_data={}
    )
    
    with patch.object(executor.task_queue, 'complete') as mock_complete:
        result = await executor._execute_step(step)
        
        assert result["step_id"] == "test-1"
        mock_complete.assert_called_once()
```

**Step 3: 运行测试**

```bash
pytest tests/agents/test_executor.py -v
```

Expected: 2 tests PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: add AgentExecutor execution engine"
```

---

### Task 7: 实现 API 端点

**Files:**
- Create: `apps/api/app/api/v1/endpoints/agents.py`
- Modify: `apps/api/app/api/v1/router.py`
- Test: `apps/api/tests/api/test_agents_api.py`

**Step 1: 创建 API 端点**

```python
# apps/api/app/api/v1/endpoints/agents.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.agents.engine.executor import agent_executor
from app.agents.engine.task_queue import task_queue

router = APIRouter()


class ExecuteRequest(BaseModel):
    """执行请求"""
    input: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ExecuteResponse(BaseModel):
    """执行响应"""
    session_id: str
    plan_id: str
    status: str
    intent: Dict[str, Any]
    total_steps: int
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/execute", response_model=ExecuteResponse)
async def execute_request(request: ExecuteRequest):
    """
    执行用户请求
    
    触发 Agent 执行流程：
    1. 意图识别
    2. 任务规划
    3. 任务入队
    4. 异步执行
    """
    try:
        result = await agent_executor.execute_user_request(
            user_input=request.input,
            session_id=request.session_id,
            context=request.context
        )
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result)
        
        return ExecuteResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = task_queue.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task.get("status"),
        result=task.get("result"),
        error=task.get("error")
    )


@router.get("/queue/status")
async def get_queue_status():
    """获取队列状态"""
    return {
        "pending": task_queue.get_queue_length(),
        # TODO: 添加 processing, completed, failed 数量
    }


@router.post("/process-queue")
async def start_queue_processor(background_tasks: BackgroundTasks):
    """启动队列处理器（后台任务）"""
    background_tasks.add_task(agent_executor.process_queue)
    return {"message": "Queue processor started"}
```

**Step 2: 更新路由**

```python
# apps/api/app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, prds, ai, tools, agents

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(prds.router, prefix="/prds", tags=["prds"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])  # 新增
```

**Step 3: 编写 API 测试**

```python
# apps/api/tests/api/test_agents_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_execute_endpoint():
    with patch('app.api.v1.endpoints.agents.agent_executor') as mock_executor:
        mock_executor.execute_user_request = AsyncMock(return_value={
            "session_id": "test-session",
            "plan_id": "test-plan",
            "status": "queued",
            "intent": {"intent": "requirement_analysis"},
            "total_steps": 3,
            "message": "任务已入队"
        })
        
        response = client.post("/api/v1/agents/execute", json={
            "input": "我要做切片借阅平台"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["total_steps"] == 3


def test_get_task_status_not_found():
    with patch('app.api.v1.endpoints.agents.task_queue') as mock_queue:
        mock_queue.get_task_status.return_value = None
        
        response = client.get("/api/v1/agents/tasks/test-id/status")
        
        assert response.status_code == 404
```

**Step 4: 运行测试**

```bash
pytest tests/api/test_agents_api.py -v
```

Expected: 2 tests PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: add Agent API endpoints"
```

---

## 第四阶段：集成测试和部署

### Task 8: 端到端集成测试

**Files:**
- Create: `apps/api/tests/integration/test_agent_flow.py`

**Step 1: 编写集成测试**

```python
# apps/api/tests/integration/test_agent_flow.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.engine.executor import AgentExecutor
from app.agents.agents.intent_classifier import IntentClassifierAgent
from app.agents.llm_client import KimiCodingClient


@pytest.mark.asyncio
async def test_full_agent_flow():
    """测试完整 Agent 执行流程"""
    
    # Mock Kimi API
    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [
        # IntentClassifier 调用
        '{"intent": "requirement_analysis", "entities": {"product": "test"}, "confidence": 0.95}',
    ]
    
    with patch('app.agents.llm_client.LLMClientFactory.create', return_value=mock_llm):
        executor = AgentExecutor()
        executor.llm_client = mock_llm
        
        # 替换 IntentClassifier 的 LLM
        intent_agent = IntentClassifierAgent(llm_client=mock_llm)
        from app.agents.base import agent_registry
        agent_registry._agents["intent-classifier"] = intent_agent
        
        # 执行请求
        result = await executor.execute_user_request("我要做测试产品")
        
        assert result["status"] == "queued"
        assert result["intent"]["intent"] == "requirement_analysis"
        assert result["total_steps"] == 3


@pytest.mark.asyncio
async def test_task_queue_integration():
    """测试任务队列集成"""
    from app.agents.engine.task_queue import TaskQueue
    
    # 使用 mock Redis
    with patch('app.agents.engine.task_queue.redis.from_url') as mock_redis:
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        queue = TaskQueue("redis://localhost")
        
        # 测试入队
        task = {"task_id": "test-1", "agent_id": "intent-classifier"}
        queue.enqueue(task)
        
        mock_client.lpush.assert_called_once()
```

**Step 2: 运行集成测试**

```bash
pytest tests/integration/ -v
```

Expected: 2 tests PASS

**Step 3: Commit**

```bash
git add -A
git commit -m "test: add integration tests for agent system"
```

---

### Task 9: 启动脚本和文档

**Files:**
- Create: `apps/api/start_agents.py`
- Modify: `apps/api/README.md`

**Step 1: 创建启动脚本**

```python
# apps/api/start_agents.py
#!/usr/bin/env python3
"""
Agent 系统启动脚本
启动队列处理器和后端服务
"""
import asyncio
import uvicorn
from app.agents.engine.executor import agent_executor


async def run_queue_processor():
    """运行队列处理器"""
    print("🚀 Starting Agent Queue Processor...")
    await agent_executor.process_queue()


def run_api_server():
    """运行 API 服务器"""
    print("🌐 Starting API Server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        # 启动队列处理器
        asyncio.run(run_queue_processor())
    else:
        # 启动 API 服务器
        run_api_server()
```

**Step 2: 更新文档**

```markdown
# apps/api/README.md

## Agent 系统

### 启动服务

```bash
# 1. 启动 Redis
docker-compose up -d redis

# 2. 启动 API 服务器
python start_agents.py

# 3. 启动队列处理器（另开终端）
python start_agents.py worker
```

### API 使用

```bash
# 执行 Agent 任务
curl -X POST http://localhost:8000/api/v1/agents/execute \
  -H "Content-Type: application/json" \
  -d '{"input": "我要做切片借阅平台，帮我分析需求"}'

# 查询任务状态
curl http://localhost:8000/api/v1/agents/tasks/{task_id}/status
```
```

**Step 3: Commit**

```bash
git add -A
git commit -m "docs: add agent system startup scripts and documentation"
```

---

## 计划完成

本计划包含 **9个主要任务**，预计开发时间 **2-3周**。

### 已完成的基础
- ✅ Agent 基类和注册表
- ✅ Kimi Coding API 客户端
- ✅ IntentClassifier Agent
- ✅ TaskPlanner 任务规划器
- ✅ Redis 任务队列
- ✅ AgentExecutor 执行引擎
- ✅ API 端点
- ✅ 集成测试
- ✅ 启动脚本

### 下一步
1. 实现剩余 4-5 个核心 Agent（RequirementAnalyst, CompetitorAnalyst, PRDWriter, ComplianceChecker, ReviewPreparer）
2. 实现工具系统
3. 实现记忆系统
4. 前端集成

**执行方式选择：**
- **选项1**：在当前会话使用 subagent-driven-development 逐个任务执行
- **选项2**：新开会话使用 executing-plans 批量执行

**请选择执行方式开始实施？**

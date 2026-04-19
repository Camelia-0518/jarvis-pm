# Jarvis PM 技术架构全面优化报告

> 生成日期: 2026-04-10  
> 版本: v1.0  
> 状态: 待实施

---

## 执行摘要

本报告基于 10 个专业技能（tech-architect, api-design, performance-optimization, refactoring, security-audit, agent-development, mcp-integration, coding-standards, test-driven-development, systematic-debugging）对 Jarvis PM 技术架构进行全面分析和优化建议。

### 关键发现

| 维度 | 现状评分 | 目标评分 | 优先级 |
|------|----------|----------|--------|
| 整体架构 | 6/10 | 9/10 | P0 |
| Agent 系统 | 7/10 | 9/10 | P0 |
| API 设计 | 6/10 | 8/10 | P1 |
| 数据库设计 | 5/10 | 8/10 | P1 |
| 性能优化 | 5/10 | 8/10 | P1 |
| 安全架构 | 4/10 | 9/10 | P0 |
| 代码质量 | 6/10 | 8/10 | P2 |
| MCP 集成 | 2/10 | 7/10 | P2 |

---

## 1. 整体架构优化

### 1.1 现状分析

当前架构采用前后端分离模式，但存在以下问题：

```
┌─────────────────────────────────────────────────────────────┐
│                        当前架构                              │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 14)                                      │
│  ├─ 页面路由 (pages router)                                  │
│  ├─ Zustand 状态管理                                         │
│  └─ Socket.io 客户端                                         │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                          │
│  ├─ 同步 SQLite (开发环境)                                   │
│  ├─ 简单任务队列 (asyncio.Queue)                             │
│  ├─ Agent 管理器 (单例模式)                                  │
│  └─ WebSocket 管理器                                         │
├─────────────────────────────────────────────────────────────┤
│  AI Layer                                                   │
│  └─ Kimi CLI 客户端 (subprocess)                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 架构问题识别

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| 数据库使用 SQLite | 高 | 并发性能差，不适合生产 |
| 无缓存层 | 高 | 重复计算，响应慢 |
| 任务队列过于简单 | 中 | 无持久化，重启丢任务 |
| 无服务发现 | 中 | 扩展困难 |
| 单点故障 | 高 | 无高可用设计 |

### 1.3 目标架构设计

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           目标架构 (微服务化)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Web App    │    │  Desktop App │    │   Mobile     │                  │
│  │  (Next.js 15)│    │  (Electron)  │    │   (PWA)      │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                          │
│         └───────────────────┼───────────────────┘                          │
│                             │                                              │
│                    ┌────────┴────────┐                                     │
│                    │   API Gateway   │  (Kong/Nginx)                        │
│                    │  - 限流/认证    │                                     │
│                    │  - 负载均衡     │                                     │
│                    └────────┬────────┘                                     │
│                             │                                              │
│  ┌──────────────────────────┼──────────────────────────┐                  │
│  │                          │                          │                  │
│  ▼                          ▼                          ▼                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │  Agent Service  │  │   PRD Service   │  │  Project Svc    │           │
│  │  ├─ Task Queue  │  │  ├─ Templates   │  │  ├─ CRUD        │           │
│  │  ├─ Executor    │  │  ├─ Generator   │  │  ├─ Search      │           │
│  │  └─ Registry    │  │  └─ Versioning  │  │  └─ Export      │           │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘           │
│           │                    │                    │                     │
│           └────────────────────┼────────────────────┘                     │
│                                │                                          │
│  ┌─────────────────────────────┼─────────────────────────────┐           │
│  │                             ▼                             │           │
│  │              ┌─────────────────────────┐                  │           │
│  │              │     Message Queue       │                  │           │
│  │              │    (Redis/RabbitMQ)     │                  │           │
│  │              └─────────────────────────┘                  │           │
│  │ Infrastructure Layer                                       │           │
│  ├───────────────────────────────────────────────────────────┤           │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │           │
│  │  │ PostgreSQL  │  │    Redis    │  │  MinIO/S3   │       │           │
│  │  │  (Primary)  │  │  (Cache)    │  │  (Files)    │       │           │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │           │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │           │
│  │  │Elasticsearch│  │  Prometheus │  │    Jaeger   │       │           │
│  │  │  (Search)   │  │  (Metrics)  │  │  (Tracing)  │       │           │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │           │
│  └───────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 架构优化建议

#### 1.4.1 数据库迁移（P0）

**从 SQLite 迁移到 PostgreSQL**

```python
# 当前配置 (config.py)
DATABASE_URL: str = "sqlite+aiosqlite:///./jarvis_pm.db"  # ❌

# 目标配置
DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/jarvis_pm"  # ✅
```

**连接池优化**

```python
# database.py 优化
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=QueuePool,
    pool_size=20,              # 连接池大小
    max_overflow=10,           # 最大溢出连接
    pool_pre_ping=True,        # 连接健康检查
    pool_recycle=3600,         # 连接回收时间
)
```

#### 1.4.2 引入缓存层（P0）

```python
# core/cache.py
import redis.asyncio as redis
from functools import wraps
import json
import hashlib

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
    
    async def get(self, key: str) -> any:
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: any, ttl: int = 3600):
        await self.redis.setex(key, ttl, json.dumps(value))
    
    def cached(self, ttl: int = 3600, key_prefix: str = ""):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
                
                # 尝试从缓存获取
                cached = await self.get(cache_key)
                if cached is not None:
                    return cached
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 写入缓存
                await self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

# 使用示例
@cache_manager.cached(ttl=300, key_prefix="agent")
async def get_agent_info(agent_id: str):
    return await db.get_agent(agent_id)
```

#### 1.4.3 任务队列升级（P1）

**从 asyncio.Queue 迁移到 Celery + Redis**

```python
# celery_config.py
from celery import Celery

celery_app = Celery(
    "jarvis_pm",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["app.tasks.agents"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,  # 公平调度
)

# tasks/agents.py
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_agent_task(self, agent_name: str, input_data: dict):
    """执行 Agent 任务（支持重试）"""
    try:
        manager = AgentManager()
        agent_id = manager.create_agent(agent_name)
        
        # 使用 asyncio 运行异步代码
        import asyncio
        result = asyncio.run(manager.execute_task(agent_id, input_data))
        
        return {
            "success": result.success,
            "output": result.output,
            "data": result.data,
            "execution_time": result.execution_time
        }
    except Exception as exc:
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "success": False,
                "error": str(exc),
                "retries_exceeded": True
            }
```

---

## 2. Agent 系统优化

### 2.1 现状问题

| 问题 | 描述 | 影响 |
|------|------|------|
| 单例模式滥用 | AgentRegistry 使用单例 | 测试困难，状态污染 |
| 无状态管理 | Agent 状态转换不清晰 | 难以追踪和恢复 |
| 缺乏编排 | 多 Agent 协作机制缺失 | 复杂任务难以分解 |
| 无记忆系统 | 每次执行都是独立的 | 无法学习和优化 |
| 工具系统简单 | 工具注册和发现机制弱 | 扩展性差 |

### 2.2 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Multi-Agent 架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Agent Orchestrator                     │   │
│  │              (任务分解、调度、监控)                      │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                         │
│       ┌───────────────┼───────────────┐                        │
│       │               │               │                        │
│       ▼               ▼               ▼                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                    │
│  │  PRD    │    │  Req    │    │ Review  │                    │
│  │ Agent   │    │ Agent   │    │ Agent   │                    │
│  └────┬────┘    └────┬────┘    └────┬────┘                    │
│       │               │               │                        │
│       └───────────────┼───────────────┘                        │
│                       │                                         │
│  ┌────────────────────┴────────────────────┐                   │
│  │              Shared Layer               │                   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐   │                   │
│  │  │  Memory │ │  Tools  │ │  LLM    │   │                   │
│  │  │  Store  │ │  Registry│ │ Client  │   │                   │
│  │  └─────────┘ └─────────┘ └─────────┘   │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 状态机重构

```python
# agents/state_machine.py
from enum import Enum, auto
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

class AgentState(Enum):
    """Agent 执行状态"""
    IDLE = auto()
    PLANNING = auto()      # 新增：规划中
    EXECUTING = auto()     # 重命名：执行中
    WAITING = auto()       # 新增：等待用户/外部
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    RECOVERING = auto()    # 新增：恢复中

@dataclass
class StateTransition:
    """状态转换定义"""
    from_state: AgentState
    to_state: AgentState
    validator: Optional[Callable] = None
    on_transition: Optional[Callable] = None

class StateMachine:
    """Agent 状态机"""
    
    # 定义允许的状态转换
    TRANSITIONS: Dict[AgentState, List[AgentState]] = {
        AgentState.IDLE: [AgentState.PLANNING, AgentState.EXECUTING],
        AgentState.PLANNING: [AgentState.EXECUTING, AgentState.WAITING, AgentState.FAILED],
        AgentState.EXECUTING: [AgentState.WAITING, AgentState.PAUSED, AgentState.COMPLETED, AgentState.FAILED],
        AgentState.WAITING: [AgentState.EXECUTING, AgentState.FAILED, AgentState.CANCELLED],
        AgentState.PAUSED: [AgentState.EXECUTING, AgentState.CANCELLED],
        AgentState.FAILED: [AgentState.RECOVERING, AgentState.IDLE],
        AgentState.RECOVERING: [AgentState.EXECUTING, AgentState.FAILED],
    }
    
    def __init__(self):
        self._state = AgentState.IDLE
        self._state_history: List[Dict] = []
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> AgentState:
        return self._state
    
    async def transition(self, new_state: AgentState, context: dict = None) -> bool:
        """执行状态转换"""
        async with self._lock:
            if new_state not in self.TRANSITIONS.get(self._state, []):
                raise InvalidStateTransition(f"Cannot transition from {self._state} to {new_state}")
            
            old_state = self._state
            self._state = new_state
            
            # 记录历史
            self._state_history.append({
                "from": old_state,
                "to": new_state,
                "timestamp": datetime.now().isoformat(),
                "context": context
            })
            
            return True
    
    def can_transition(self, new_state: AgentState) -> bool:
        """检查是否可以转换到目标状态"""
        return new_state in self.TRANSITIONS.get(self._state, [])
    
    def get_history(self) -> List[Dict]:
        """获取状态历史"""
        return self._state_history.copy()

class InvalidStateTransition(Exception):
    pass
```

### 2.4 记忆系统实现

```python
# agents/memory.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np
from enum import Enum

class MemoryType(Enum):
    FACT = "fact"              # 事实记忆
    PREFERENCE = "preference"  # 用户偏好
    DECISION = "decision"      # 决策记录
    CONTEXT = "context"        # 上下文
    FEEDBACK = "feedback"      # 反馈

@dataclass
class Memory:
    """记忆单元"""
    id: str
    type: MemoryType
    content: str
    embedding: Optional[List[float]] = None
    timestamp: datetime = None
    importance: float = 0.5  # 0-1
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

class MemoryStore:
    """三层记忆存储"""
    
    def __init__(self, redis_client, db_session):
        self.redis = redis_client  # 工作记忆
        self.db = db_session       # 长期记忆
        self._working_memory: Dict[str, Memory] = {}  # 当前会话记忆
    
    async def add(self, memory: Memory, persist: bool = True):
        """添加记忆"""
        # 存入工作记忆
        self._working_memory[memory.id] = memory
        
        # 存入 Redis（短期）
        await self.redis.setex(
            f"memory:{memory.id}",
            3600,  # 1小时过期
            json.dumps(self._memory_to_dict(memory))
        )
        
        # 持久化到数据库
        if persist:
            await self._persist_memory(memory)
    
    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 5
    ) -> List[Memory]:
        """检索记忆（基于语义相似度）"""
        # 1. 从工作记忆检索
        working_results = self._search_working_memory(query, memory_type)
        
        # 2. 从 Redis 检索
        redis_results = await self._search_redis(query, memory_type)
        
        # 3. 从数据库检索（向量搜索）
        db_results = await self._search_db(query, memory_type, limit)
        
        # 合并结果，按重要性排序
        all_results = working_results + redis_results + db_results
        all_results.sort(key=lambda m: m.importance, reverse=True)
        
        return all_results[:limit]
    
    async def compress(self, session_id: str) -> str:
        """压缩会话记忆为摘要"""
        memories = [
            m for m in self._working_memory.values()
            if m.metadata.get("session_id") == session_id
        ]
        
        if not memories:
            return ""
        
        # 使用 LLM 生成摘要
        summary = await self._generate_summary(memories)
        
        # 保存压缩后的记忆
        compressed = Memory(
            id=f"compressed_{session_id}",
            type=MemoryType.CONTEXT,
            content=summary,
            importance=0.8
        )
        await self.add(compressed)
        
        # 清理原始记忆
        for m in memories:
            del self._working_memory[m.id]
        
        return summary
    
    def _memory_to_dict(self, memory: Memory) -> dict:
        return {
            "id": memory.id,
            "type": memory.type.value,
            "content": memory.content,
            "timestamp": memory.timestamp.isoformat(),
            "importance": memory.importance,
            "tags": memory.tags,
            "metadata": memory.metadata
        }
```

### 2.5 Agent 编排器

```python
# agents/orchestrator.py
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import uuid

class TaskType(Enum):
    SEQUENTIAL = "sequential"    # 顺序执行
    PARALLEL = "parallel"        # 并行执行
    CONDITIONAL = "conditional"  # 条件执行
    LOOP = "loop"                # 循环执行

@dataclass
class SubTask:
    """子任务定义"""
    id: str
    agent_name: str
    input_data: Dict[str, Any]
    dependencies: List[str]  # 依赖的其他子任务ID
    task_type: TaskType = TaskType.SEQUENTIAL
    condition: Optional[Callable] = None  # 条件执行的条件函数
    max_retries: int = 3

@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    tasks: List[SubTask]
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None

class AgentOrchestrator:
    """Agent 编排器"""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self._workflows: Dict[str, Workflow] = {}
        self._results: Dict[str, Any] = {}
    
    async def execute_workflow(
        self,
        workflow: Workflow,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行工作流"""
        self._workflows[workflow.id] = workflow
        context = context or {}
        
        try:
            # 构建依赖图
            dependency_graph = self._build_dependency_graph(workflow.tasks)
            
            # 执行拓扑排序
            execution_order = self._topological_sort(dependency_graph)
            
            # 按顺序执行任务
            for task_id in execution_order:
                task = next(t for t in workflow.tasks if t.id == task_id)
                
                # 检查条件
                if task.condition and not task.condition(context):
                    continue
                
                # 准备输入数据（合并依赖任务的输出）
                input_data = self._prepare_input(task, context)
                
                # 执行任务
                result = await self._execute_subtask(task, input_data)
                
                # 存储结果
                self._results[task_id] = result
                context[f"task_{task_id}_result"] = result
                
                if not result.get("success") and task.task_type != TaskType.CONDITIONAL:
                    # 任务失败，调用错误处理
                    if workflow.on_error:
                        await workflow.on_error(task, result, context)
                    raise TaskExecutionError(f"Task {task_id} failed: {result.get('error')}")
            
            # 工作流完成
            if workflow.on_complete:
                await workflow.on_complete(context)
            
            return {
                "success": True,
                "workflow_id": workflow.id,
                "results": self._results,
                "context": context
            }
            
        except Exception as e:
            return {
                "success": False,
                "workflow_id": workflow.id,
                "error": str(e),
                "completed_tasks": list(self._results.keys())
            }
    
    async def _execute_subtask(
        self,
        task: SubTask,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行子任务（支持重试）"""
        for attempt in range(task.max_retries):
            try:
                agent_id = self.agent_manager.create_agent(task.agent_name)
                record = await self.agent_manager.execute_task(
                    agent_id,
                    input_data
                )
                
                return {
                    "success": record.result.success if record.result else False,
                    "output": record.result.output if record.result else None,
                    "data": record.result.data if record.result else None,
                    "attempts": attempt + 1
                }
            except Exception as e:
                if attempt == task.max_retries - 1:
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1
                    }
                await asyncio.sleep(2 ** attempt)  # 指数退避
    
    def _build_dependency_graph(self, tasks: List[SubTask]) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {task.id: [] for task in tasks}
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in graph:
                    graph[task.id].append(dep_id)
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        visited = set()
        result = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            result.append(node)
        
        for node in graph:
            visit(node)
        
        return result
    
    def _prepare_input(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备任务输入（合并依赖结果）"""
        input_data = task.input_data.copy()
        
        for dep_id in task.dependencies:
            if dep_id in self._results:
                input_data[f"dep_{dep_id}"] = self._results[dep_id]
        
        # 添加上下文
        input_data["_context"] = context
        
        return input_data

class TaskExecutionError(Exception):
    pass
```

---

## 3. API 设计规范

### 3.1 现状问题

| 问题 | 描述 | 严重程度 |
|------|------|----------|
| 无 API 版本控制 | 路由直接 `/api/v1/...` | 中 |
| 响应格式不一致 | 有些返回 dict，有些返回对象 | 高 |
| 缺少分页 | 列表接口无分页 | 高 |
| 错误处理不规范 | HTTP 状态码使用混乱 | 中 |
| 缺少 API 文档 | 无 OpenAPI/Swagger | 中 |

### 3.2 RESTful API 规范

```python
# api/v1/responses.py
from typing import Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

class APIResponse(BaseModel):
    """标准 API 响应格式"""
    success: bool
    data: Optional[Any] = None
    error: Optional[dict] = None
    meta: dict = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorDetail(BaseModel):
    """错误详情"""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[dict] = None

class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(APIResponse):
    """分页响应"""
    data: List[Any]
    meta: PaginationMeta

# 响应构建器
class ResponseBuilder:
    @staticmethod
    def success(data: Any = None, meta: dict = None) -> APIResponse:
        return APIResponse(
            success=True,
            data=data,
            meta=meta or {"timestamp": datetime.now().isoformat()}
        )
    
    @staticmethod
    def error(
        code: str,
        message: str,
        field: str = None,
        details: dict = None,
        status_code: int = 400
    ) -> APIResponse:
        return APIResponse(
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                field=field,
                details=details
            ).dict(),
            meta={"timestamp": datetime.now().isoformat(), "status_code": status_code}
        )
    
    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        limit: int,
        total: int
    ) -> PaginatedResponse:
        total_pages = (total + limit - 1) // limit
        return PaginatedResponse(
            success=True,
            data=data,
            meta=PaginationMeta(
                page=page,
                limit=limit,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        )
```

### 3.3 统一错误处理

```python
# core/exceptions.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class AppException(Exception):
    """应用基础异常"""
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ValidationError(AppException):
    """验证错误"""
    def __init__(self, message: str, field: str = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details={"field": field}
        )

class NotFoundError(AppException):
    """资源不存在"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} with id '{identifier}' not found",
            status_code=404
        )

class AuthenticationError(AppException):
    """认证错误"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401
        )

class AuthorizationError(AppException):
    """授权错误"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message,
            status_code=403
        )

class RateLimitError(AppException):
    """限流错误"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            status_code=429,
            details={"retry_after": retry_after}
        )

# 全局异常处理器
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "meta": {"timestamp": datetime.now().isoformat()}
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors}
            },
            "meta": {"timestamp": datetime.now().isoformat()}
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            },
            "meta": {"timestamp": datetime.now().isoformat()}
        }
    )

# 在 main.py 中注册
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
```

### 3.4 分页与过滤

```python
# api/v1/dependencies.py
from fastapi import Query
from typing import Optional
from pydantic import BaseModel

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Query(1, ge=1, description="页码")
    limit: int = Query(20, ge=1, le=100, description="每页数量")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

class SortParams(BaseModel):
    """排序参数"""
    sort_by: Optional[str] = Query(None, description="排序字段")
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向")

class FilterParams(BaseModel):
    """过滤参数基类"""
    search: Optional[str] = Query(None, description="搜索关键词")
    created_after: Optional[datetime] = Query(None, description="创建时间之后")
    created_before: Optional[datetime] = Query(None, description="创建时间之前")

# 使用示例
@router.get("/projects", response_model=PaginatedResponse)
async def list_projects(
    pagination: PaginationParams = Depends(),
    sort: SortParams = Depends(),
    filters: FilterParams = Depends(),
    status: Optional[str] = Query(None, description="项目状态"),
    industry: Optional[str] = Query(None, description="行业"),
    db: AsyncSession = Depends(get_db)
):
    """获取项目列表（支持分页、排序、过滤）"""
    # 构建查询
    query = select(Project)
    
    # 应用过滤
    if filters.search:
        query = query.where(
            or_(
                Project.name.ilike(f"%{filters.search}%"),
                Project.description.ilike(f"%{filters.search}%")
            )
        )
    
    if status:
        query = query.where(Project.status == status)
    
    if industry:
        query = query.where(Project.industry == industry)
    
    if filters.created_after:
        query = query.where(Project.created_at >= filters.created_after)
    
    # 获取总数
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    
    # 应用排序
    if sort.sort_by:
        sort_column = getattr(Project, sort.sort_by, Project.created_at)
        if sort.sort_order == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)
    
    # 应用分页
    query = query.offset(pagination.offset).limit(pagination.limit)
    
    # 执行查询
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ResponseBuilder.paginated(
        data=[project.to_dict() for project in projects],
        page=pagination.page,
        limit=pagination.limit,
        total=total
    )
```

### 3.5 API 端点重构

```python
# api/v1/endpoints/agents_refactored.py
from fastapi import APIRouter, Depends, BackgroundTasks, Query
from typing import List, Optional
from uuid import UUID

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("", response_model=PaginatedResponse)
async def list_agents(
    pagination: PaginationParams = Depends(),
    capability: Optional[str] = Query(None, description="按能力过滤"),
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """
    获取 Agent 列表
    
    - 支持分页
    - 支持按能力过滤
    """
    agents = registry.get_all_info()
    
    if capability:
        agents = [a for a in agents if capability in a.get("capabilities", [])]
    
    total = len(agents)
    paginated_agents = agents[pagination.offset:pagination.offset + pagination.limit]
    
    return ResponseBuilder.paginated(
        data=paginated_agents,
        page=pagination.page,
        limit=pagination.limit,
        total=total
    )

@router.get("/{agent_name}", response_model=APIResponse)
async def get_agent(
    agent_name: str,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    """获取 Agent 详细信息"""
    agent_class = registry.get(agent_name)
    if not agent_class:
        raise NotFoundError("Agent", agent_name)
    
    return ResponseBuilder.success(data={
        "name": agent_class.name,
        "description": agent_class.description,
        "version": agent_class.version,
        "capabilities": agent_class.capabilities,
        "required_tools": agent_class.required_tools
    })

@router.post("/tasks", response_model=APIResponse, status_code=201)
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    queue: TaskQueue = Depends(get_task_queue),
    current_user: str = Depends(get_current_user_id)
):
    """
    创建 Agent 任务
    
    - 异步执行
    - 返回任务 ID 用于查询状态
    """
    task_id = await queue.submit(
        agent_name=request.agent_name,
        input_data=request.input_data,
        priority=request.priority,
        user_id=current_user
    )
    
    return ResponseBuilder.success(
        data={
            "task_id": str(task_id),
            "status": "queued",
            "estimated_wait": queue.get_estimated_wait_time()
        },
        meta={"status_code": 201}
    )

@router.get("/tasks/{task_id}", response_model=APIResponse)
async def get_task_status(
    task_id: UUID,
    queue: TaskQueue = Depends(get_task_queue)
):
    """获取任务状态和结果"""
    task = await queue.get_task(task_id)
    
    if not task:
        raise NotFoundError("Task", str(task_id))
    
    return ResponseBuilder.success(data={
        "task_id": str(task.id),
        "agent_name": task.agent_name,
        "status": task.status,
        "result": task.result.to_dict() if task.result else None,
        "error": task.error,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    })

@router.post("/tasks/{task_id}/cancel", response_model=APIResponse)
async def cancel_task(
    task_id: UUID,
    queue: TaskQueue = Depends(get_task_queue)
):
    """取消任务"""
    success = await queue.cancel_task(task_id)
    
    if not success:
        raise AppException(
            code="CANCEL_FAILED",
            message="Task cannot be cancelled (may already be completed or failed)",
            status_code=400
        )
    
    return ResponseBuilder.success(data={"message": "Task cancelled successfully"})
```

---

## 4. 数据库设计优化

### 4.1 模型关系优化

```python
# models/project_enhanced.py
from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, ForeignKey, Table, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base

# 多对多关联表
project_members = Table(
    'project_members',
    Base.metadata,
    Column('project_id', String, ForeignKey('projects.id', ondelete='CASCADE')),
    Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role', String, default='member'),  # owner, admin, member
    Column('joined_at', DateTime(timezone=True), server_default=func.now())
)

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class Project(Base):
    """增强版 Project 模型"""
    __tablename__ = 'projects'
    
    # 主键和基础字段
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)  # URL友好的名称
    description = Column(Text)
    
    # 分类和状态
    industry = Column(String(50), default="other", index=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    visibility = Column(String(20), default="private")  # private, internal, public
    
    # 外键
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(String(36), ForeignKey('organizations.id'), index=True)
    
    # JSON 配置
    settings = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)  # 扩展字段
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # 软删除
    
    # 关系
    owner = relationship("User", back_populates="owned_projects")
    members = relationship("User", secondary=project_members, back_populates="projects")
    prds = relationship("PRD", back_populates="project", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="project")
    
    # 复合索引
    __table_args__ = (
        Index('ix_project_org_status', 'organization_id', 'status'),
        Index('ix_project_created', 'created_at', 'status'),
    )
    
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name) < 1:
            raise ValueError("Project name cannot be empty")
        if len(name) > 255:
            raise ValueError("Project name too long (max 255 characters)")
        return name
    
    @validates('slug')
    def validate_slug(self, key, slug):
        import re
        if not re.match(r'^[a-z0-9-]+$', slug):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return slug
    
    def to_dict(self, include_relations: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "industry": self.industry,
            "status": self.status.value,
            "visibility": self.visibility,
            "created_by": self.created_by,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_relations:
            data["prds"] = [prd.to_dict() for prd in self.prds]
            data["member_count"] = len(self.members)
        
        return data
    
    def soft_delete(self):
        """软删除"""
        self.status = ProjectStatus.DELETED
        self.deleted_at = func.now()
```

### 4.2 PRD 模型增强

```python
# models/prd_enhanced.py
from sqlalchemy import Column, String, DateTime, Enum, JSON, ForeignKey, Text, Integer, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import uuid
import enum

class PRDStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    ARCHIVED = "archived"

class PRDVersion(Base):
    """PRD 版本历史"""
    __tablename__ = 'prd_versions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prd_id = Column(String(36), ForeignKey('prds.id', ondelete='CASCADE'), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    content = Column(JSON, nullable=False)
    markdown = Column(Text)
    change_summary = Column(Text)  # 变更摘要
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    prd = relationship("PRD", back_populates="versions")

class PRD(Base):
    """增强版 PRD 模型"""
    __tablename__ = 'prds'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False, index=True)
    
    # 基础信息
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    version = Column(String(20), default="1.0")
    status = Column(Enum(PRDStatus), default=PRDStatus.DRAFT, index=True)
    
    # 内容（结构化存储）
    content = Column(JSON, default=dict)  # 章节结构化数据
    markdown = Column(Text)  # 完整 Markdown
    outline = Column(JSON, default=list)  # 大纲结构
    
    # AI 生成元数据
    ai_generated = Column(JSON, default=dict)
    ai_model = Column(String(50))  # 使用的模型
    generation_params = Column(JSON, default=dict)  # 生成参数
    
    # 统计信息
    word_count = Column(Integer, default=0)
    section_count = Column(Integer, default=0)
    
    # 外键
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    current_version_id = Column(String(36), ForeignKey('prd_versions.id'))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))
    
    # 关系
    project = relationship("Project", back_populates="prds")
    versions = relationship("PRDVersion", back_populates="prd", cascade="all, delete-orphan")
    current_version = relationship("PRDVersion", foreign_keys=[current_version_id])
    
    # 索引
    __table_args__ = (
        Index('ix_prd_project_status', 'project_id', 'status'),
        Index('ix_prd_created', 'created_at'),
    )
    
    def to_dict(self, include_content: bool = True) -> dict:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "slug": self.slug,
            "version": self.version,
            "status": self.status.value,
            "word_count": self.word_count,
            "section_count": self.section_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_content:
            data["content"] = self.content
            data["markdown"] = self.markdown
            data["outline"] = self.outline
        
        return data
    
    def create_version(self, user_id: str) -> PRDVersion:
        """创建新版本"""
        version = PRDVersion(
            prd_id=self.id,
            version=self.version,
            content=self.content,
            markdown=self.markdown,
            created_by=user_id
        )
        return version
```

### 4.3 数据库迁移脚本

```python
# alembic/versions/001_initial_schema.py
"""Initial schema with optimizations"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')  # 用于全文搜索
    
    # 创建组织表
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # 创建用户表（增强）
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('preferences', postgresql.JSONB, default={}),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # 创建项目表（增强）
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('industry', sa.String(50), default='other', index=True),
        sa.Column('status', sa.Enum('active', 'archived', 'deleted', name='project_status'), default='active'),
        sa.Column('visibility', sa.String(20), default='private'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('organization_id', sa.String(36), sa.ForeignKey('organizations.id')),
        sa.Column('settings', postgresql.JSONB, default={}),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.Index('ix_project_org_status', 'organization_id', 'status'),
        sa.Index('ix_project_created', 'created_at', 'status'),
    )
    
    # 创建项目成员关联表
    op.create_table(
        'project_members',
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('role', sa.String(20), default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('project_id', 'user_id'),
    )
    
    # 创建 PRD 表（增强）
    op.create_table(
        'prds',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('version', sa.String(20), default='1.0'),
        sa.Column('status', sa.Enum('draft', 'in_review', 'approved', 'implemented', 'archived', name='prd_status'), default='draft'),
        sa.Column('content', postgresql.JSONB, default={}),
        sa.Column('markdown', sa.Text),
        sa.Column('outline', postgresql.JSONB, default=[]),
        sa.Column('ai_generated', postgresql.JSONB, default={}),
        sa.Column('ai_model', sa.String(50)),
        sa.Column('generation_params', postgresql.JSONB, default={}),
        sa.Column('word_count', sa.Integer, default=0),
        sa.Column('section_count', sa.Integer, default=0),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Index('ix_prd_project_status', 'project_id', 'status'),
        sa.Index('ix_prd_created', 'created_at'),
    )
    
    # 创建 PRD 版本表
    op.create_table(
        'prd_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('prd_id', sa.String(36), sa.ForeignKey('prds.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False),
        sa.Column('markdown', sa.Text),
        sa.Column('change_summary', sa.Text),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # 添加全文搜索索引
    op.execute('''
        CREATE INDEX idx_project_name_trgm ON projects 
        USING gin (name gin_trgm_ops);
    ''')
    
    op.execute('''
        CREATE INDEX idx_prd_title_trgm ON prds 
        USING gin (title gin_trgm_ops);
    ''')

def downgrade():
    op.drop_table('prd_versions')
    op.drop_table('prds')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('users')
    op.drop_table('organizations')
    op.execute('DROP TYPE IF EXISTS project_status')
    op.execute('DROP TYPE IF EXISTS prd_status')
```

---

## 5. 性能优化方案

### 5.1 缓存策略

```python
# core/cache_strategies.py
from typing import Any, Optional, Callable
from functools import wraps
import json
import hashlib
import asyncio
from datetime import datetime, timedelta

class CacheStrategy:
    """缓存策略基类"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        raise NotImplementedError
    
    async def delete(self, key: str):
        raise NotImplementedError
    
    async def invalidate_pattern(self, pattern: str):
        """按模式删除缓存"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

class ReadThroughCache(CacheStrategy):
    """读穿透缓存"""
    
    async def get_or_set(
        self,
        key: str,
        loader: Callable,
        ttl: int = 3600
    ) -> Any:
        """获取缓存，不存在则加载"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # 加载数据
        value = await loader()
        await self.set(key, value, ttl)
        return value

class WriteThroughCache(CacheStrategy):
    """写穿透缓存"""
    
    async def set_and_invalidate(
        self,
        key: str,
        value: Any,
        invalidate_patterns: list[str],
        ttl: int = 3600
    ):
        """写入缓存并失效相关缓存"""
        await self.set(key, value, ttl)
        
        # 失效相关缓存
        for pattern in invalidate_patterns:
            await self.invalidate_pattern(pattern)

class CacheAside(CacheStrategy):
    """旁路缓存（最常用）"""
    
    def cached(self, ttl: int = 3600, key_prefix: str = ""):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self._generate_key(key_prefix, func.__name__, args, kwargs)
                
                # 尝试从缓存获取
                cached = await self.get(cache_key)
                if cached is not None:
                    return cached
                
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 写入缓存
                await self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    def _generate_key(self, prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_data = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        hash_key = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{hash_key}" if prefix else hash_key

# 具体缓存实现
class RedisCache(CacheAside):
    """Redis 缓存实现"""
    
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        await self.redis.setex(key, ttl, json.dumps(value, default=str))
    
    async def delete(self, key: str):
        await self.redis.delete(key)

# 多级缓存
class MultiLevelCache:
    """L1: 内存缓存, L2: Redis 缓存"""
    
    def __init__(self, redis_client, maxsize: int = 1000):
        self.l1 = {}  # 内存缓存
        self.l2 = RedisCache(redis_client)
        self.maxsize = maxsize
        self._access_order = []
    
    async def get(self, key: str) -> Optional[Any]:
        # L1 查询
        if key in self.l1:
            self._update_access_order(key)
            return self.l1[key]
        
        # L2 查询
        value = await self.l2.get(key)
        if value is not None:
            # 回填 L1
            self._set_l1(key, value)
        
        return value
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        self._set_l1(key, value)
        await self.l2.set(key, value, ttl)
    
    def _set_l1(self, key: str, value: Any):
        """设置 L1 缓存（带 LRU 淘汰）"""
        if len(self.l1) >= self.maxsize and key not in self.l1:
            # 淘汰最久未使用的
            oldest = self._access_order.pop(0)
            del self.l1[oldest]
        
        self.l1[key] = value
        self._update_access_order(key)
    
    def _update_access_order(self, key: str):
        """更新访问顺序"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
```

### 5.2 数据库查询优化

```python
# core/query_optimizer.py
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from typing import List, Type

class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def optimize_pagination(query, page: int, limit: int):
        """优化分页查询"""
        # 使用游标分页替代 OFFSET（大数据量时）
        if page > 100:  # 大页码时使用游标
            return query  # 返回原查询，由调用方处理游标
        
        offset = (page - 1) * limit
        return query.offset(offset).limit(limit)
    
    @staticmethod
    def eager_load_relations(query, model: Type, relations: List[str]):
        """优化关联加载"""
        for relation in relations:
            attr = getattr(model, relation)
            
            # 根据关联类型选择加载策略
            if attr.property.uselist:
                # 一对多使用 selectinload
                query = query.options(selectinload(attr))
            else:
                # 多对一使用 joinedload
                query = query.options(joinedload(attr))
        
        return query
    
    @staticmethod
    def add_select_only(query, columns: List):
        """只选择需要的列"""
        return query.with_entities(*columns)
    
    @staticmethod
    def use_exists_instead_of_count(query):
        """存在性检查优化"""
        # 将 SELECT COUNT(*) 改为 EXISTS
        return query.with_entities(func.exists().select_from(query.subquery()))

# 使用示例
async def get_projects_optimized(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    limit: int = 20
):
    """优化后的项目查询"""
    
    # 基础查询
    query = select(Project).where(
        Project.created_by == user_id,
        Project.status == ProjectStatus.ACTIVE
    )
    
    # 优化关联加载
    query = QueryOptimizer.eager_load_relations(
        query,
        Project,
        relations=["owner", "prds"]  # 预加载
    )
    
    # 优化分页
    query = QueryOptimizer.optimize_pagination(query, page, limit)
    
    # 执行查询
    result = await db.execute(query)
    return result.scalars().all()
```

### 5.3 异步优化

```python
# core/async_optimizer.py
import asyncio
from typing import List, Callable, Any
from concurrent.futures import ThreadPoolExecutor

class AsyncOptimizer:
    """异步优化工具"""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def gather_with_limit(
        self,
        tasks: List[Callable],
        limit: int = 5,
        *args,
        **kwargs
    ) -> List[Any]:
        """限制并发数的 gather"""
        semaphore = asyncio.Semaphore(limit)
        
        async def bounded_task(task):
            async with semaphore:
                return await task(*args, **kwargs)
        
        return await asyncio.gather(*[bounded_task(t) for t in tasks])
    
    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: func(*args, **kwargs)
        )
    
    @staticmethod
    async def batch_process(
        items: List[Any],
        processor: Callable,
        batch_size: int = 100,
        delay: float = 0.1
    ) -> List[Any]:
        """批量处理（带延迟，避免过载）"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(*[processor(item) for item in batch])
            results.extend(batch_results)
            
            # 批次间延迟
            if i + batch_size < len(items):
                await asyncio.sleep(delay)
        
        return results

# 连接池优化
class ConnectionPoolOptimizer:
    """连接池优化配置"""
    
    @staticmethod
    def get_optimized_engine_args():
        """获取优化的引擎参数"""
        return {
            "pool_size": 20,              # 基础连接数
            "max_overflow": 30,           # 最大溢出连接
            "pool_pre_ping": True,        # 连接健康检查
            "pool_recycle": 3600,         # 连接回收时间
            "pool_timeout": 30,           # 获取连接超时
            "echo": False,                # 关闭 SQL 日志（生产环境）
        }
    
    @staticmethod
    def get_optimized_session_args():
        """获取优化的会话参数"""
        return {
            "expire_on_commit": False,    # 提交后不过期
            "autocommit": False,
            "autoflush": False,           # 手动控制 flush
        }
```

---

## 6. 安全加固方案

### 6.1 安全审计发现

| 问题 | 风险等级 | 位置 |
|------|----------|------|
| 硬编码密钥 | 严重 | config.py |
| 无输入验证 | 高 | API 端点 |
| 无速率限制 | 中 | API 层 |
| 无审计日志 | 中 | 全局 |
| CORS 配置过宽 | 中 | main.py |
| SQL 注入风险 | 低 | 使用 ORM |

### 6.2 配置安全

```python
# core/config_secure.py
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import secrets

class SecureSettings(BaseSettings):
    """安全配置（生产环境）"""
    
    # 应用配置
    APP_NAME: str = "Jarvis PM API"
    DEBUG: bool = False  # 生产环境关闭
    ENV: str = "production"
    
    # 安全密钥（强制从环境变量获取）
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # 必须设置
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v
    
    # 数据库（强制使用 PostgreSQL）
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if "sqlite" in v.lower():
            raise ValueError("SQLite is not allowed in production")
        return v
    
    # JWT 配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 缩短有效期
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    
    # CORS（严格限制）
    CORS_ORIGINS: List[str] = Field(default_factory=list)
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # 速率限制
    RATE_LIMIT_REQUESTS: int = 100  # 每窗口请求数
    RATE_LIMIT_WINDOW: int = 60     # 窗口大小（秒）
    
    # 文件上传
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {"md", "txt", "pdf", "doc", "docx"}
    
    # AI API 密钥
    KIMI_API_KEY: str = Field(..., env="KIMI_API_KEY")
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # 日志
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# 生成安全密钥的脚本
def generate_secure_key():
    """生成安全密钥"""
    return secrets.token_urlsafe(32)
```

### 6.3 输入验证与防护

```python
# core/security_input.py
from fastapi import HTTPException
from pydantic import BaseModel, validator, Field
import re
from html import escape

class SanitizedString(str):
    """自动清理的字符串类型"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError("string required")
        # 清理 HTML
        return cls(escape(v))

class XSSProtection:
    """XSS 防护"""
    
    # 危险模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    @classmethod
    def sanitize(cls, content: str) -> str:
        """清理内容"""
        for pattern in cls.DANGEROUS_PATTERNS:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        return escape(content)
    
    @classmethod
    def validate(cls, content: str) -> bool:
        """验证内容是否安全"""
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return False
        return True

class SQLInjectionProtection:
    """SQL 注入防护"""
    
    # SQL 关键字（用于检测，不是阻止）
    SQL_KEYWORDS = [
        'UNION', 'SELECT', 'INSERT', 'UPDATE', 'DELETE',
        'DROP', 'CREATE', 'ALTER', 'EXEC', 'EXECUTE'
    ]
    
    @classmethod
    def detect(cls, value: str) -> bool:
        """检测潜在的 SQL 注入"""
        upper_value = value.upper()
        keyword_count = sum(1 for kw in cls.SQL_KEYWORDS if kw in upper_value)
        return keyword_count >= 2  # 多个关键字可能有问题
    
    @classmethod
    def validate_order_by(cls, field: str, allowed_fields: list) -> str:
        """验证排序字段"""
        if field not in allowed_fields:
            raise HTTPException(status_code=400, detail="Invalid sort field")
        return field

# 请求模型示例
class CreateProjectRequest(BaseModel):
    """创建项目请求（带验证）"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    industry: str = Field(default="other")
    
    @validator('name')
    def validate_name(cls, v):
        # 检查 XSS
        if not XSSProtection.validate(v):
            raise ValueError("Name contains invalid characters")
        return XSSProtection.sanitize(v)
    
    @validator('description')
    def validate_description(cls, v):
        return XSSProtection.sanitize(v)
    
    @validator('industry')
    def validate_industry(cls, v):
        allowed = ['medical', 'ecommerce', 'saas', 'education', 'other']
        if v not in allowed:
            raise ValueError(f"Industry must be one of: {allowed}")
        return v
```

### 6.4 速率限制

```python
# middleware/rate_limit.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, Tuple
import redis.asyncio as redis

class RateLimiter:
    """速率限制器（滑动窗口）"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict]:
        """
        检查是否允许请求
        
        Returns:
            (allowed, headers)
        """
        now = time.time()
        window_start = now - window
        
        # 使用 Redis Sorted Set 实现滑动窗口
        pipe = self.redis.pipeline()
        
        # 移除窗口外的请求记录
        pipe.zremrangebyscore(key, 0, window_start)
        
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        
        # 设置过期时间
        pipe.expire(key, window)
        
        results = await pipe.execute()
        current_count = results[1]
        
        allowed = current_count <= limit
        
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - current_count)),
            "X-RateLimit-Reset": str(int(now + window)),
        }
        
        if not allowed:
            headers["X-RateLimit-Retry-After"] = str(window)
        
        return allowed, headers

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(
        self,
        app,
        redis_client: redis.Redis,
        default_limit: int = 100,
        default_window: int = 60
    ):
        super().__init__(app)
        self.limiter = RateLimiter(redis_client)
        self.default_limit = default_limit
        self.default_window = default_window
        
        # 不同路径的不同限制
        self.path_limits = {
            "/api/v1/auth/login": (5, 60),      # 登录限制更严格
            "/api/v1/agents/tasks": (20, 60),   # Agent 任务限制
        }
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端标识
        client_id = self._get_client_id(request)
        path = request.url.path
        
        # 获取限制配置
        limit, window = self.path_limits.get(
            path,
            (self.default_limit, self.default_window)
        )
        
        # 生成限流键
        key = f"rate_limit:{client_id}:{path}"
        
        # 检查限流
        allowed, headers = await self.limiter.is_allowed(key, limit, window)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers=headers
            )
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加限流头
        for header, value in headers.items():
            response.headers[header] = value
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用认证用户 ID
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # 否则使用 IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
```

### 6.5 审计日志

```python
# middleware/audit_log.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import json
import uuid

class AuditLogMiddleware(BaseHTTPMiddleware):
    """审计日志中间件"""
    
    # 敏感字段（需要脱敏）
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'api_key', 'authorization',
        'credit_card', 'ssn', 'phone', 'email'
    }
    
    def __init__(self, app, logger, db_session_factory):
        super().__init__(app)
        self.logger = logger
        self.db_session_factory = db_session_factory
    
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = datetime.now()
        
        # 记录请求
        await self._log_request(request, request_id)
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 记录响应
            await self._log_response(request, response, request_id, start_time)
            
            # 添加请求 ID 头
            response.headers["X-Request-ID"] = request_id
            
            return response
        except Exception as e:
            # 记录错误
            await self._log_error(request, e, request_id, start_time)
            raise
    
    async def _log_request(self, request: Request, request_id: str):
        """记录请求"""
        body = await self._get_request_body(request)
        
        log_data = {
            "event": "request",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "user_id": getattr(request.state, "user_id", None),
            "body": self._sanitize_data(body) if body else None,
        }
        
        self.logger.info(f"Request: {json.dumps(log_data)}")
    
    async def _log_response(
        self,
        request: Request,
        response,
        request_id: str,
        start_time: datetime
    ):
        """记录响应"""
        duration = (datetime.now() - start_time).total_seconds()
        
        log_data = {
            "event": "response",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "status_code": response.status_code,
            "duration_ms": int(duration * 1000),
        }
        
        self.logger.info(f"Response: {json.dumps(log_data)}")
    
    async def _log_error(
        self,
        request: Request,
        error: Exception,
        request_id: str,
        start_time: datetime
    ):
        """记录错误"""
        duration = (datetime.now() - start_time).total_seconds()
        
        log_data = {
            "event": "error",
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": int(duration * 1000),
        }
        
        self.logger.error(f"Error: {json.dumps(log_data)}")
    
    async def _get_request_body(self, request: Request) -> dict:
        """获取请求体"""
        try:
            body = await request.body()
            return json.loads(body) if body else None
        except:
            return None
    
    def _sanitize_data(self, data: dict) -> dict:
        """脱敏数据"""
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
```

---

## 7. 代码质量与重构

### 7.1 代码坏味道识别

| 坏味道 | 位置 | 严重程度 | 重构建议 |
|--------|------|----------|----------|
| 重复代码 | `os.environ['PYTHONIOENCODING']` 多处 | 低 | 提取到模块级 |
| 过长函数 | `PRDAgent.execute()` | 中 | 提取子函数 |
| 过大类 | `AgentManager` | 中 | 分离职责 |
| 魔法字符串 | 状态字符串 | 低 | 使用枚举 |
| 注释过多 | 部分文件 | 低 | 自解释代码 |

### 7.2 重构计划

#### Phase 1: 基础重构（P2）

```python
# 1. 提取常量
# constants/agent.py
class AgentConstants:
    DEFAULT_MAX_STEPS = 50
    DEFAULT_TIMEOUT = 300
    DEFAULT_MAX_RETRIES = 3
    
    ENCODING = 'utf-8'

# 2. 提取工具函数
# utils/encoding.py
import os

def ensure_utf8_encoding():
    """确保 UTF-8 编码"""
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# 3. 使用枚举替代魔法字符串
# enums/agent.py
from enum import Enum, auto

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

#### Phase 2: 类重构（P2）

```python
# 重构 AgentManager - 分离职责

# agents/lifecycle.py
class AgentLifecycleManager:
    """Agent 生命周期管理"""
    
    def __init__(self):
        self._instances: Dict[UUID, BaseAgent] = {}
    
    def create(self, agent_class: Type[BaseAgent], **kwargs) -> UUID:
        """创建 Agent 实例"""
        agent = agent_class(**kwargs)
        self._instances[agent.id] = agent
        return agent.id
    
    def get(self, agent_id: UUID) -> Optional[BaseAgent]:
        return self._instances.get(agent_id)
    
    def destroy(self, agent_id: UUID):
        """销毁 Agent 实例"""
        if agent_id in self._instances:
            del self._instances[agent_id]

# agents/execution.py
class TaskExecutionEngine:
    """任务执行引擎"""
    
    async def execute(
        self,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        timeout: int = None
    ) -> AgentResult:
        """执行任务（带超时）"""
        timeout = timeout or AgentConstants.DEFAULT_TIMEOUT
        
        try:
            return await asyncio.wait_for(
                agent.execute(input_data),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return AgentResult(
                success=False,
                error=f"Execution timeout after {timeout}s"
            )

# agents/monitoring.py
class ExecutionMonitor:
    """执行监控"""
    
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {
            "task_start": [],
            "task_complete": [],
            "task_error": []
        }
    
    def on(self, event: str, callback: Callable):
        """注册事件监听"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def emit(self, event: str, data: Any):
        """触发事件"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")
```

### 7.3 代码规范实施

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## 8. MCP 集成方案

### 8.1 MCP 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Integration Layer                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  MCP Client Manager                     │   │
│  │              (管理多个 MCP Server 连接)                  │   │
│  └────────────────────┬────────────────────────────────────┘   │
│                       │                                         │
│       ┌───────────────┼───────────────┐                        │
│       │               │               │                        │
│       ▼               ▼               ▼                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                    │
│  │ Serena  │    │ GitHub  │    │  Files  │                    │
│  │  MCP    │    │  MCP    │    │  MCP    │                    │
│  └─────────┘    └─────────┘    └─────────┘                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Agent MCP Bridge                       │   │
│  │         (将 MCP Tools 暴露给 Agent 使用)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 MCP 客户端实现

```python
# mcp/client.py
from typing import Dict, List, Any, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    parameters: dict
    server: str

@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str
    mime_type: str

class MCPClientManager:
    """MCP 客户端管理器"""
    
    def __init__(self):
        self._clients: Dict[str, Any] = {}  # server_name -> client
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
    
    async def connect_server(
        self,
        name: str,
        command: str,
        args: List[str] = None,
        env: dict = None
    ):
        """连接 MCP Server"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env
        )
        
        # 建立连接
        stdio_transport = await stdio_client(server_params)
        stdio, write = stdio_transport
        session = await ClientSession(stdio, write)
        await session.initialize()
        
        self._clients[name] = session
        
        # 发现工具和资源
        await self._discover_capabilities(name, session)
    
    async def _discover_capabilities(self, server_name: str, session):
        """发现 Server 能力"""
        # 发现工具
        tools_response = await session.list_tools()
        for tool in tools_response.tools:
            mcp_tool = MCPTool(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
                server=server_name
            )
            self._tools[f"{server_name}:{tool.name}"] = mcp_tool
        
        # 发现资源
        resources_response = await session.list_resources()
        for resource in resources_response.resources:
            mcp_resource = MCPResource(
                uri=resource.uri,
                name=resource.name,
                description=resource.description,
                mime_type=resource.mimeType
            )
            self._resources[resource.uri] = mcp_resource
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict,
        server: str = None
    ) -> Any:
        """调用 MCP 工具"""
        # 查找工具
        if server:
            full_name = f"{server}:{tool_name}"
        else:
            # 在所有 server 中查找
            full_name = None
            for key in self._tools:
                if key.endswith(f":{tool_name}"):
                    full_name = key
                    break
        
        if not full_name or full_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool = self._tools[full_name]
        session = self._clients[tool.server]
        
        # 调用工具
        result = await session.call_tool(tool_name, arguments)
        return result
    
    async def read_resource(self, uri: str) -> Any:
        """读取 MCP 资源"""
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")
        
        resource = self._resources[uri]
        session = self._clients.get(resource.server)
        
        if not session:
            raise ValueError(f"Server not connected for resource: {uri}")
        
        result = await session.read_resource(uri)
        return result
    
    def list_tools(self, server: str = None) -> List[MCPTool]:
        """列出可用工具"""
        tools = list(self._tools.values())
        if server:
            tools = [t for t in tools if t.server == server]
        return tools
    
    async def disconnect_all(self):
        """断开所有连接"""
        for session in self._clients.values():
            await session.close()
        self._clients.clear()
```

### 8.3 MCP 配置

```json
{
  "mcpServers": {
    "serena": {
      "command": "npx",
      "args": ["-y", "@serena/mcp-server"],
      "env": {
        "SERENA_API_KEY": "${SERENA_API_KEY}"
      },
      "enabled": true
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@github/mcp-server"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      },
      "enabled": false
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
      "enabled": true
    }
  }
}
```

### 8.4 Agent 集成 MCP

```python
# agents/mcp_bridge.py
from typing import Dict, Any, List
from .tools.base import BaseTool

class MCPToolBridge(BaseTool):
    """MCP 工具桥接"""
    
    def __init__(self, mcp_manager: MCPClientManager):
        self.mcp_manager = mcp_manager
    
    async def execute(self, tool_name: str, parameters: dict) -> dict:
        """执行 MCP 工具"""
        try:
            result = await self.mcp_manager.call_tool(tool_name, parameters)
            return {
                "success": True,
                "output": result.content if hasattr(result, 'content') else str(result),
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_tools(self) -> List[dict]:
        """获取可用工具列表（供 Agent 使用）"""
        tools = self.mcp_manager.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in tools
        ]

# 在 Agent 中使用
class EnhancedAgent(BaseAgent):
    """增强版 Agent（支持 MCP）"""
    
    def __init__(self, mcp_manager: MCPClientManager = None, **kwargs):
        super().__init__(**kwargs)
        self.mcp_bridge = MCPToolBridge(mcp_manager) if mcp_manager else None
        self.available_tools = self._load_tools()
    
    def _load_tools(self) -> List[dict]:
        """加载所有可用工具"""
        tools = []
        
        # 内置工具
        tools.extend(self._get_builtin_tools())
        
        # MCP 工具
        if self.mcp_bridge:
            tools.extend(self.mcp_bridge.get_available_tools())
        
        return tools
    
    async def _call_tool(self, tool_name: str, parameters: dict) -> dict:
        """调用工具（支持 MCP）"""
        # 检查是否是 MCP 工具
        if self.mcp_bridge and any(
            t["name"] == tool_name 
            for t in self.mcp_bridge.get_available_tools()
        ):
            return await self.mcp_bridge.execute(tool_name, parameters)
        
        # 内置工具
        return await super()._call_tool(tool_name, parameters)
```

---

## 9. 实施路线图

### 9.1 优先级矩阵

```
紧急程度 ^
         |
    高   |  [P0] 数据库迁移    [P0] 安全加固
         |  [P0] 缓存层        [P0] Agent 状态机
         |
    中   |  [P1] API 重构      [P1] 任务队列
         |  [P1] 性能优化      [P1] 数据库优化
         |
    低   |  [P2] MCP 集成      [P2] 代码重构
         |  [P2] 代码规范      [P2] 审计日志
         |
         +----------------------------------->
              低          中          高    影响程度
```

### 9.2 实施计划

#### Sprint 1 (Week 1-2): 基础设施
- [ ] 数据库迁移 SQLite -> PostgreSQL
- [ ] 配置管理安全加固
- [ ] 错误处理标准化
- [ ] 基础监控搭建

#### Sprint 2 (Week 3-4): 核心优化
- [ ] Redis 缓存层实现
- [ ] Agent 状态机重构
- [ ] API 响应标准化
- [ ] 输入验证与 XSS 防护

#### Sprint 3 (Week 5-6): 性能与安全
- [ ] 任务队列 Celery 迁移
- [ ] 速率限制实现
- [ ] 数据库查询优化
- [ ] 审计日志系统

#### Sprint 4 (Week 7-8): 高级特性
- [ ] Agent 编排器实现
- [ ] 记忆系统开发
- [ ] MCP 集成基础
- [ ] 代码重构与规范

### 9.3 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据库迁移失败 | 中 | 高 | 完整备份，回滚方案 |
| 性能优化无效 | 低 | 中 | 基准测试，渐进优化 |
| 安全漏洞遗漏 | 中 | 高 | 安全审计，渗透测试 |
| 开发进度延迟 | 中 | 中 | 分期实施，MVP 优先 |

---

## 10. 总结与建议

### 10.1 关键改进点

1. **架构层面**: 从单体向微服务演进，引入缓存层和消息队列
2. **Agent 系统**: 状态机 + 记忆系统 + 编排器，支持复杂工作流
3. **API 设计**: 标准化响应格式，完善错误处理，添加分页和过滤
4. **数据库**: 迁移到 PostgreSQL，优化索引和查询
5. **安全**: 全面加固，包括输入验证、速率限制、审计日志
6. **性能**: 多级缓存，异步优化，连接池调优
7. **MCP**: 集成外部工具，扩展 Agent 能力

### 10.2 立即行动项

1. **今天**: 备份数据，准备 PostgreSQL 环境
2. **本周**: 完成数据库迁移和基础安全配置
3. **本月**: 实现缓存层和 API 标准化

### 10.3 长期愿景

将 Jarvis PM 打造成企业级 AI 产品管理平台，支持：
- 多租户架构
- 水平扩展
- 企业级安全合规
- 丰富的 MCP 生态集成

---

*报告完成 - 2026-04-10*  
*作者: Claude Code with 10 Skills*  
*版本: v1.0*

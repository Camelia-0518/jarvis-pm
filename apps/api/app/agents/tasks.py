#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列

提供异步任务执行功能（基于 asyncio）
简化版本，无需外部依赖
"""

import os
import logging

os.environ['PYTHONIOENCODING'] = 'utf-8'

import asyncio
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .base import AgentResult
from .manager import AgentManager

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueuedTask:
    """队列中的任务"""
    id: UUID
    agent_name: str
    input_data: Dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    callback: Optional[Callable] = None
    status: str = "pending"
    result: Optional[AgentResult] = None
    error: Optional[str] = None
    progress_updates: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.progress_updates is None:
            self.progress_updates = []

    def add_progress(self, step: str, message: str, data: Dict[str, Any] = None):
        """添加进度更新"""
        self.progress_updates.append({
            "step": step,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        })


class TaskQueue:
    """
    异步任务队列

    基于 asyncio 的简单任务队列，无需外部依赖
    """

    def __init__(self, max_workers: int = 3):
        """
        初始化任务队列

        Args:
            max_workers: 最大并发工作数
        """
        self.max_workers = max_workers
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: Dict[UUID, QueuedTask] = {}
        self._manager = AgentManager()
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self):
        """启动任务队列"""
        if self._running:
            return

        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop())
            for _ in range(self.max_workers)
        ]

    async def stop(self):
        """停止任务队列"""
        self._running = False

        # 取消所有工作器
        for worker in self._workers:
            worker.cancel()

        # 等待工作器完成
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []

        # 清理已完成的 Agent 实例
        self._manager.cleanup()

    async def submit(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None
    ) -> UUID:
        """
        提交任务到队列

        Args:
            agent_name: Agent 名称
            input_data: 输入数据
            priority: 优先级
            callback: 完成回调

        Returns:
            任务 ID
        """
        task = QueuedTask(
            id=uuid4(),
            agent_name=agent_name,
            input_data=input_data,
            priority=priority,
            created_at=datetime.now(),
            callback=callback
        )

        self._tasks[task.id] = task

        # 根据优先级设置队列优先级（数值越小优先级越高）
        await self._queue.put((-priority.value, task.id))

        return task.id

    async def get_task(self, task_id: UUID) -> Optional[QueuedTask]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> list[QueuedTask]:
        """
        列出任务

        Args:
            status: 按状态筛选 (pending, running, completed, failed)
        """
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def _worker_loop(self):
        """工作器循环"""
        while self._running:
            try:
                # 获取任务（带超时以便检查停止信号）
                priority, task_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                await self._execute_task(task_id)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def _execute_task(self, task_id: UUID):
        """执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return

        task.status = "running"
        task.add_progress("started", "任务开始执行")

        try:
            # 创建 Agent 实例
            agent_id = self._manager.create_agent(task.agent_name)
            if not agent_id:
                raise ValueError(f"Failed to create agent: {task.agent_name}")

            # 执行任务
            record = await self._manager.execute_task(
                agent_id,
                task.input_data
            )

            task.result = record.result
            task.status = "completed" if record.result and record.result.success else "failed"
            task.error = record.error

            # 提取执行步骤信息作为进度
            steps_info = []
            if record.result and record.result.metadata:
                steps_info = record.result.metadata.get("steps_completed", 0)
                mode = record.result.metadata.get("mode", "full")
                task.add_progress(
                    "completed",
                    f"任务完成（{mode} 模式）",
                    {
                        "steps_completed": steps_info,
                        "mode": mode,
                        "execution_time": record.result.execution_time,
                        "evaluated": record.result.metadata.get("evaluated", False),
                    }
                )

            # 触发回调
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(task)
                    else:
                        task.callback(task)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.add_progress("failed", f"任务失败: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        pending = sum(1 for t in self._tasks.values() if t.status == "pending")
        running = sum(1 for t in self._tasks.values() if t.status == "running")
        completed = sum(1 for t in self._tasks.values() if t.status == "completed")
        failed = sum(1 for t in self._tasks.values() if t.status == "failed")

        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total": len(self._tasks),
            "queue_size": self._queue.qsize(),
            "workers": len(self._workers)
        }


# 全局队列实例
_queue_instance: Optional[TaskQueue] = None


def get_task_queue(max_workers: int = 3) -> TaskQueue:
    """获取全局任务队列实例"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = TaskQueue(max_workers=max_workers)
    return _queue_instance


async def submit_task(
    agent_name: str,
    input_data: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL
) -> UUID:
    """
    便捷函数：提交任务

    Args:
        agent_name: Agent 名称
        input_data: 输入数据
        priority: 优先级

    Returns:
        任务 ID
    """
    queue = get_task_queue()
    if not queue._running:
        await queue.start()

    return await queue.submit(agent_name, input_data, priority)
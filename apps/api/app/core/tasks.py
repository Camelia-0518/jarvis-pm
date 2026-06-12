"""In-memory async task queue for prototype skeleton extraction.

Tasks are stored in memory and executed via asyncio.create_task.
This is lightweight and sufficient for development; for production,
replace with Celery/RQ + Redis.
"""

import asyncio
import logging
import time
import traceback
import uuid
from typing import Dict, Any, Optional, Callable, Awaitable
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Task store with LRU + TTL cleanup
MAX_TASK_STORE_SIZE = 1000
TASK_TTL_SECONDS = 3600  # 1 hour

_task_store: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_store_lock = asyncio.Lock()

# Active asyncio tasks to prevent garbage collection
_active_tasks: Dict[str, asyncio.Task] = {}


async def _cleanup_old_tasks() -> None:
    """Remove completed/failed tasks older than TTL; LRU evict if still over limit."""
    async with _store_lock:
        now = time.time()
        # Remove expired completed/failed tasks
        expired = [
            tid for tid, task in list(_task_store.items())
            if task["status"] in ("done", "failed") and now - task["updated_at"] > TASK_TTL_SECONDS
        ]
        for tid in expired:
            _task_store.pop(tid, None)

        # LRU eviction if still over limit
        while len(_task_store) > MAX_TASK_STORE_SIZE:
            # Prefer removing oldest completed/failed task
            oldest = None
            oldest_time = float("inf")
            for tid, task in list(_task_store.items()):
                if task["status"] in ("done", "failed"):
                    if task["created_at"] < oldest_time:
                        oldest_time = task["created_at"]
                        oldest = tid
            if oldest:
                _task_store.pop(oldest, None)
            else:
                # All tasks are active; do NOT evict pending/running tasks.
                # Accept temporary over-limit to preserve active task state.
                break


async def create_task(
    prd_content: str,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a new async task and return its ID."""
    await _cleanup_old_tasks()
    task_id = str(uuid.uuid4())
    async with _store_lock:
        _task_store[task_id] = {
            "task_id": task_id,
            "status": "pending",  # pending / extracting / generating / done / failed
            "prd_content": prd_content,
            "options": options or {},
            "skeleton": None,
            "html": None,
            "report": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    return task_id


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task by ID. Updates LRU order on access."""
    async with _store_lock:
        task = _task_store.get(task_id)
        if task is not None:
            _task_store.move_to_end(task_id)
    return task


async def update_task(
    task_id: str,
    status: Optional[str] = None,
    skeleton: Optional[Dict[str, Any]] = None,
    html: Optional[str] = None,
    report: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """Update task fields."""
    async with _store_lock:
        task = _task_store.get(task_id)
        if not task:
            logger.warning("Attempted to update non-existent task: %s", task_id)
            return
        if status:
            task["status"] = status
        if skeleton is not None:
            task["skeleton"] = skeleton
        if html is not None:
            task["html"] = html
        if report is not None:
            task["report"] = report
        if error is not None:
            task["error"] = error
        task["updated_at"] = time.time()


async def run_task(
    task_id: str,
    coro: Callable[[str, Optional[Dict[str, Any]]], Awaitable[Dict[str, Any]]],
    on_done: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    on_error: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> None:
    """Run a coroutine in background and update task status."""
    task = get_task(task_id)
    if not task:
        return

    try:
        await update_task(task_id, status="extracting")
        result = await coro(task["prd_content"], task["options"])
        await update_task(task_id, status="done", skeleton=result)
        if on_done:
            await on_done(task_id, result)
    except Exception:
        await update_task(
            task_id,
            status="failed",
            error=f"{traceback.format_exc()}",
        )
        if on_error:
            await on_error(task_id, traceback.format_exc())
    finally:
        _active_tasks.pop(task_id, None)


async def start_background_task(
    task_id: str,
    coro: Callable[[str, Optional[Dict[str, Any]]], Awaitable[Dict[str, Any]]],
    on_done: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    on_error: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> None:
    """Start a background asyncio task. Must be called from a running event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    bg_task = loop.create_task(run_task(task_id, coro, on_done, on_error))
    _active_tasks[task_id] = bg_task

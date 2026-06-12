"""轻量级熔断器实现（零依赖）"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    CLOSED = "closed"      # 正常通行
    OPEN = "open"          # 熔断，快速失败
    HALF_OPEN = "half_open"  # 半开，允许试探请求


class CircuitBreakerError(Exception):
    """熔断器打开时抛出的异常"""
    pass


class CircuitBreaker:
    """异步熔断器

    Args:
        fail_max: 连续失败多少次后熔断
        reset_timeout: 熔断后多少秒进入半开状态
        expected_exception: 视为失败的异常类型元组
    """

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: float = 60.0,
        expected_exception: tuple = (Exception,),
        name: str = "default",
    ):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.expected_exception = expected_exception
        self.name = name

        self._state = CircuitState.CLOSED
        self._fail_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            # 检查是否已过超时时间，应转入半开
            if self._last_failure_time and (time.time() - self._last_failure_time) >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker '%s' entering HALF_OPEN state", self.name)
        return self._state

    async def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """在熔断器保护下执行异步函数"""
        async with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                logger.warning("Circuit breaker '%s' is OPEN, fast-failing", self.name)
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN after {self.fail_max} consecutive failures. "
                    f"Retry after {self.reset_timeout}s."
                )

        # 半开状态下只允许一个请求通过（由锁保证）
        try:
            result = await fn(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        async with self._lock:
            self._fail_count = 0
            self._last_failure_time = None
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker '%s' recovered, state=CLOSED", self.name)

    async def _on_failure(self):
        async with self._lock:
            self._fail_count += 1
            self._last_failure_time = time.time()
            if self._fail_count >= self.fail_max:
                self._state = CircuitState.OPEN
                logger.error(
                    "Circuit breaker '%s' OPENED after %d consecutive failures",
                    self.name, self.fail_max
                )

    def __call__(self, fn: Callable[..., T]) -> Callable[..., T]:
        """装饰器用法"""
        async def wrapper(*args, **kwargs):
            return await self.call(fn, *args, **kwargs)
        return wrapper

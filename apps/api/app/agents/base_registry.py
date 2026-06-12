"""泛型注册表基类

消除 AgentRegistry 和 ToolRegistry 之间的重复单例/CRUD 模式。
子类需定义 _items: Dict[str, Type[T]] 和 __new__ 单例逻辑。
"""

import logging
from typing import Dict, List, Type, TypeVar, Generic, Optional

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRegistry(Generic[T]):
    """泛型注册表 — CRUD 操作, __contains__, __len__。

    子类需自行实现:
      - __new__ (单例 + _items 初始化)
      - create_instance
      - get_all_info
    """

    # ---------- CRUD ----------

    def register(self, item_class: Type[T], *, allow_duplicate: bool = True) -> Type[T]:
        """注册类型。allow_duplicate=False 时重复注册抛出 ValueError。"""
        name = getattr(item_class, "name", item_class.__name__)
        if name in self._items:
            if not allow_duplicate:
                raise ValueError(f"Already registered: {name}")
            return item_class
        self._items[name] = item_class
        return item_class

    def unregister(self, name: str) -> None:
        self._items.pop(name, None)

    def get(self, name: str) -> Optional[Type[T]]:
        return self._items.get(name)

    def list(self) -> List[str]:
        return list(self._items.keys())

    def clear(self) -> None:
        self._items.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)

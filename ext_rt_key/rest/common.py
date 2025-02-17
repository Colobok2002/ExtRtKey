"""
:mod:`common` -- Базовый класс для создания rout
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from logging import getLogger, Logger
from typing import Any

from fastapi import APIRouter

from ext_rt_key.rest.manager import RTManger


class RoutsCommon(ABC):
    """Абстрактный класс для rout"""

    def __init__(
        self,
        rt_manger: RTManger,
        prefix: str = "",
        tags: list[str | Enum] | None = None,
        logger: Logger | None = None,
    ):
        """
        :param prefix: Префикс для всех маршрутов в этом роутере.
        :param tags: Теги, используемые для группировки маршрутов в документации.
        """
        self._router = APIRouter(prefix=prefix, tags=tags)
        self.logger = logger or getLogger(__name__)
        self.rt_manger = rt_manger

    def add_route(self, path: str, endpoint: Callable[..., Any], method: str = "GET") -> None:
        """
        Добавляет маршрут в роутер.

        :param path: URL-путь маршрута.
        :param endpoint: Функция-обработчик запроса.
        :param method: HTTP-метод (GET, POST и т. д.).
        """
        self._router.add_api_route(path, endpoint, methods=[method])

    @abstractmethod
    def setup_routes(self) -> None:
        """Абстрактный метод для настройки маршрутов. Должен быть реализован в подклассах."""
        pass

    @property
    def router(self) -> APIRouter:
        """Возвращает роутер."""
        self.setup_routes()
        return self._router

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

from ext_rt_key.models import db as models
from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.manager import RTManger
from ext_rt_key.utils.db_helper import DBHelper


class CustomAPIRouter(APIRouter):
    """Расширенный APIRouter"""

    def add_api_route(self, *args: Any, **kwargs: Any) -> None:
        """Ext добавем параметр OPTIONS по умолчанию"""
        if "methods" in kwargs and "OPTIONS" not in kwargs["methods"]:
            kwargs["methods"].append("OPTIONS")

        super().add_api_route(*args, **kwargs)


class RoutsCommon(ABC):
    """Абстрактный класс для rout"""

    def __init__(
        self,
        rt_manger: RTManger,
        db_helper: DBHelper,
        prefix: str = "",
        tags: list[str | Enum] | None = None,
        logger: Logger | None = None,
    ):
        """
        :param prefix: Префикс для всех маршрутов в этом роутере.
        :param tags: Теги, используемые для группировки маршрутов в документации.
        """
        self._router = CustomAPIRouter(prefix=prefix, tags=tags)
        self.logger = logger or getLogger(__name__)
        self.rt_manger = rt_manger
        self.db_helper = db_helper
        self.models = models

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
        raise NotImplementedError()

    @property
    def router(self) -> APIRouter:
        """Возвращает роутер."""
        self.setup_routes()
        return self._router

    @staticmethod
    def good_response(
        message: str = "Успешно",
        data: dict[str, Any] | None = None,
    ) -> GoodResponse:
        """
        Успешный результат

        :param message: Сообщение, defaults to "Успешно"
        :param data: Полезная нагрузка, defaults to None
        :return: GoodResponse
        """
        return GoodResponse(
            message=message,
            data=data,
        )

    @staticmethod
    def bad_response(
        message: str = "Что то пошло не так",
        data: dict[str, Any] | None = None,
    ) -> BadResponse:
        """
        Результат с ошибкой

        :param message: Сообщение, defaults to "Что то пошло не так"
        :param data: Полезная нагрузка, defaults to None
        :return: BadResponse
        """
        return BadResponse(
            message=message,
            data=data,
        )

    def get_user_id(self, jwt_token: str) -> int | None:
        """Получает внутренний id user если он есть"""
        with self.db_helper.sessionmanager() as session:
            user_model = (
                session.query(self.models.User)
                .filter(self.models.User.jwt_token == jwt_token)
                .first()
            )
            if user_model:
                return user_model.id
            return None

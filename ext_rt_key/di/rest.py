"""
:mod:`rest` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
import time
from typing import Any, cast

import yaml
from dependency_injector import containers, providers
from fastapi import FastAPI, Request, Response
from fastapi_offline import FastAPIOffline

from ext_rt_key import __version__
from ext_rt_key.di.common import CommonDI
from ext_rt_key.rest.common import RoutsCommon
from ext_rt_key.rest.pong import PingRouter

__all__ = ("RestDI",)


class CustomFastAPIType(FastAPI):
    """Кастомный тип FastApi чтоб добавить атрибут logger"""

    logger: Logger


def init_rest_app(
    ping_router: RoutsCommon,
    logger: Logger,
) -> FastAPI:
    """
    Инициализация Rest интерфейса


    :return: Экземпляр :class:`FastAPIOffline`
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:  # noqa: ARG001, RUF029
        # Ожидание запуска сервисов от которых зависит приложение
        logger.info("Приложение инициализировано")
        yield

    app: CustomFastAPIType = cast(
        CustomFastAPIType, FastAPIOffline(version=__version__, lifespan=lifespan)
    )

    # app.include_router(heath.router)
    # app.include_router(actions.router)
    app.include_router(ping_router.router)

    app.logger = logger

    @app.middleware("http")
    async def timing_middleware(request: Request, call_next: Any) -> Any:
        """Middleware для автоматического замера времени выполнения ВСЕХ маршрутов в FastAPI."""
        start_time = time.time()

        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"Маршрут {request.url.path} выполнен за {duration:.4f} секунд.",
        )

        return response

    logger.info("Зарегистрированные routs", extra={"routs": ping_router.router.routes})
    return app


class RestDI(containers.DeclarativeContainer):
    """DI-контейнер с основными зависимостями"""

    common_di = providers.Container(CommonDI)

    ping_router = providers.Singleton(
        PingRouter,
        prefix="/ping",
        tags=["ping"],
    )

    app = providers.Factory(
        init_rest_app,
        ping_router=ping_router,
        logger=common_di.logger,
    )

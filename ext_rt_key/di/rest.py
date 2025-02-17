"""
:mod:`rest` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any, cast

from dependency_injector import containers, providers
from fastapi import FastAPI, Request
from fastapi_offline import FastAPIOffline

from ext_rt_key import __version__
from ext_rt_key.di.common import CommonDI
from ext_rt_key.rest.auth.auth_router import AuthRouter
from ext_rt_key.rest.common import RoutsCommon
from ext_rt_key.rest.manager import RTManger

__all__ = ("RestDI",)


class CustomFastAPIType(FastAPI):
    """Кастомный тип FastApi чтоб добавить атрибут logger"""

    logger: Logger


def init_rest_app(
    auth_router: RoutsCommon,
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
    app.include_router(auth_router.router)

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

    logger.info("Зарегистрированные routs", extra={"routs": app.router.routes})
    return app


class RestDI(containers.DeclarativeContainer):
    """DI-контейнер с основными зависимостями"""

    common_di = providers.Container(CommonDI)

    rt_manger = providers.Singleton(
        RTManger,
        logger=common_di.logger,
    )

    auth_router = providers.Singleton(
        AuthRouter,
        rt_manger=rt_manger,
        prefix="/auth",
        tags=["auth"],
    )

    app = providers.Factory(
        init_rest_app,
        auth_router=auth_router,
        logger=common_di.logger,
    )

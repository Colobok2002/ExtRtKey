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
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine

from ext_rt_key import __appname__, __version__
from ext_rt_key.di.common import CommonDI
from ext_rt_key.rest.auth.auth_router import AuthRouter
from ext_rt_key.rest.common import RoutsCommon
from ext_rt_key.rest.devices.devices_router import DevicesRouter
from ext_rt_key.rest.manager import RTManger
from ext_rt_key.rest.video.video_router import VideoRouter
from ext_rt_key.utils.db_helper import DBHelper

__all__ = ("RestDI",)


class CustomFastAPIType(FastAPI):
    """Кастомный тип FastApi чтоб добавить атрибут logger"""

    logger: Logger


def init_rest_app(
    routers: list[type[RoutsCommon]],
    logger: Logger,
    settings: BaseSettings,
) -> FastAPI:
    """
    Инициализация Rest интерфейса


    :return: Экземпляр :class:`FastAPIOffline`
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[Any]:  # noqa: ARG001, RUF029
        # Ожидание запуска сервисов от которых зависит приложение
        logger.info("Приложение инициализировано", extra={"settings": settings.model_dump_json()})
        yield

    app: CustomFastAPIType = cast(
        CustomFastAPIType, FastAPIOffline(version=__version__, lifespan=lifespan)
    )

    for router in routers:
        app.include_router(router().router)  # type: ignore

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


def get_db_helper(
    url: str,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> DBHelper:
    pool_size = pool_size or 5
    max_overflow = max_overflow or 10
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        connect_args={"application_name": __appname__},
    )

    return DBHelper(engine=engine)


class RestDI(containers.DeclarativeContainer):
    """DI-контейнер с основными зависимостями"""

    common_di = providers.Container(CommonDI)

    db_helper: DBHelper = providers.Resource(
        get_db_helper,  # type: ignore
        url=common_di.settings.provided().DB_URL,
    )

    rt_manger = providers.Singleton(
        RTManger,
        logger=common_di.logger,
        db_helper=db_helper,
    )

    auth_router = providers.Singleton(
        AuthRouter,
        rt_manger=rt_manger,
        prefix="/auth",
        tags=["auth"],
        db_helper=db_helper,
    )

    video_router = providers.Singleton(
        VideoRouter,
        rt_manger=rt_manger,
        prefix="/video",
        tags=["video"],
        db_helper=db_helper,
    )

    devices_router = providers.Singleton(
        DevicesRouter,
        rt_manger=rt_manger,
        prefix="/devices",
        tags=["devices"],
        db_helper=db_helper,
    )

    app = providers.Factory(
        init_rest_app,
        routers=[
            auth_router,
            video_router,
            devices_router,
        ],
        logger=common_di.logger,
        settings=common_di.settings,
    )

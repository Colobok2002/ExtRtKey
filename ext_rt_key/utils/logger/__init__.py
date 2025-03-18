"""
:mod:`__init__` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from collections.abc import Callable
from logging import (
    getLogger,
    getLoggerClass,
    getLogRecordFactory,
    Logger,
    LogRecord,
    setLoggerClass,
    setLogRecordFactory,
)
from textwrap import indent
from typing import Any

import yaml

from ext_rt_key.utils.logger.utils import PrettyDumper

__all__ = (
    "extend_log_record",
    "get_logger",
    "get_record_fields",
)


# Наименование атрибута для хранения extra параметрами
_EXTRA_ARGS_NAME = "_extra_args"
_old_record_factory: Callable[..., Any] | None = None
_old_logger_class: type[Logger] | None = None
_base_logger: Logger | None = None


class LoggerExt(Logger):
    """Расширенный class:`Logger`"""

    def makeRecord(
        self,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args: Any,
        exc_info: Any,
        func: Any = None,
        extra: Any = None,
        sinfo: Any = None,
    ) -> LogRecord:
        """Расширение базового метода: добавление атрибута `_EXTRA_ARGS_NAME` для хранения extra параметров"""
        rv = super().makeRecord(
            name=name,
            level=level,
            fn=fn,
            lno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            extra=extra,
            sinfo=sinfo,
        )

        # Добавляем дополнительный атрибут
        if extra is not None:
            if _EXTRA_ARGS_NAME in rv.__dict__:
                raise KeyError(f"Attempt to overwrite {_EXTRA_ARGS_NAME!r} in LogRecord")

            rv.__dict__[_EXTRA_ARGS_NAME] = extra

        return rv


class LogRecordExt(LogRecord):
    """Расширенный class:`LogRecord`"""

    def getMessage(self) -> str:
        """Расширение базового метода: добавление в сообщение extra параметров (если они были переданы)"""
        msg = super().getMessage()

        extra = getattr(self, _EXTRA_ARGS_NAME, None)

        if extra:
            if msg[-1:] != "\n":
                msg += "\n"
            msg += "Extra args (YAML):\n"
            # msg += indent(yaml.dump(extra, Dumper=PrettyDumper), ' ├──> ')
            msg += indent(yaml.dump(extra, Dumper=PrettyDumper), " └──> ")[:-1]

        return msg


def get_logger(name: str, extra: bool = True) -> Logger:
    """
    Переопределение класса логгера на class:`LoggerExt` и инициализация логгеров.
    Если базовый логгер не определен, то создает его, если определен, то создает логгер дочерний от базового.
    Для базового логгера устанавливается свойство `propagate` = False.

    :param name: Имя логгера
    :param extra: Добавить обработчик extra параметров (в этом случае extra параметры выгружаются в лог)
    """
    global _base_logger
    global _old_record_factory
    global _old_logger_class
    if _base_logger is None:
        if extra:
            if _old_record_factory is None:
                _old_record_factory = getLogRecordFactory()

            if _old_logger_class is None:
                _old_logger_class = getLoggerClass()

            setLoggerClass(LoggerExt)
            setLogRecordFactory(LogRecordExt)

        _base_logger = getLogger(name)
        # По умолчанию отключаем передачу записей лога по иерархии логгеров, т.к. предполагается, что
        # для родительского логгера будут заданы собственные обработчики, чтобы не смешивать вывод фреймворков
        # (SQLAlchemy, FastAPI, Celery и т.д.) и вывод приложения
        _base_logger.propagate = False

        return _base_logger

    return _base_logger.getChild(name)


def extend_log_record(**_kwargs: Any) -> None:
    """
    Расширение записи лога статическими атрибутами

    :param _kwargs: Список атрибутов со значениями
    """
    old_factory = getLogRecordFactory()

    global _old_record_factory
    if _old_record_factory is None:
        _old_record_factory = old_factory

    def record_factory(*args: Any, **kwargs: Any) -> Any:
        record = old_factory(*args, **kwargs)

        for k, v in _kwargs.items():
            record.__setattr__(k, v)

        return record

    setLogRecordFactory(record_factory)


def get_record_fields(
    record: LogRecord | LogRecordExt,
    exclude_fields: list[str] | None = None,
    exclude_empty: bool = True,
) -> dict[str, Any]:
    """
    Формирование атрибутов записи лога

    :param record: Запись лога
    :param exclude_fields: Список наименований исключаемых атрибутов
    :param exclude_empty: Исключать атрибуты, которые на содержат значений

    :return: Словарь атрибутов записи лога
    """
    _exclude_fields = []

    if exclude_fields:
        _exclude_fields.extend(exclude_fields)

    extra = getattr(record, _EXTRA_ARGS_NAME, None)
    if extra is not None:
        _exclude_fields.append(_EXTRA_ARGS_NAME)
        _exclude_fields.extend(extra.keys())

    return {
        k: v
        for k, v in record.__dict__.items()
        if k not in _exclude_fields and (not exclude_empty or v)
    }


def reset() -> None:
    """Сброс настроек"""
    global _old_logger_class
    global _old_record_factory

    if _old_logger_class is not None:
        setLoggerClass(_old_logger_class)
        _old_logger_class = None

    if _old_record_factory is not None:
        setLogRecordFactory(_old_record_factory)
        _old_record_factory = None

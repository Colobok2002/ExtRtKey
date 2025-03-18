"""
:mod:`handlers` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from logging import ERROR, LogRecord, StreamHandler
from sys import stderr, stdout
from typing import Any

from ext_rt_key.utils.logger.formatters import DefaultFormatter

__all__ = (
    "StderrHandler",
    "StdoutHandler",
)


class StdoutHandler(StreamHandler):  # type: ignore
    """
    Вывод записей журнала с уровнем < ERROR в stdout
    Установка в качестве форматтера по-умолчанию class:``
    """

    def __init__(self, stream: Any = None) -> None:
        """Переопределение конструктора: потока вывода по-умолчанию - stdout, установка фильтра записей"""
        super().__init__(stream or stdout)
        self.addFilter(self.error_record_filter)
        self.setFormatter(DefaultFormatter)

    @staticmethod
    def error_record_filter(record: LogRecord) -> bool:
        """Отправляем в stdout записи с уровнем логирование меньшим чем ERROR"""
        return record.levelno < ERROR


class StderrHandler(StreamHandler):  # type: ignore
    """Вывод записей журнала с уровнем >= ERROR в stderr"""

    def __init__(self, stream: Any = None) -> None:
        """Переопределение конструктора: установка фильтра записей"""
        super().__init__(stream or stderr)
        self.setLevel(ERROR)
        self.setFormatter(DefaultFormatter)

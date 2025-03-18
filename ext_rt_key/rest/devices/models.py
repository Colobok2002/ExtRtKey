"""
:mod:`models` -- Модели запросов для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from pydantic import BaseModel


class LoadDevices(BaseModel):
    """Запрос на погрузку устройств"""

    token: str
    login_id: int

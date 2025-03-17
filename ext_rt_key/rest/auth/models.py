"""
:mod:`models` -- Модели запросов для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from pydantic import BaseModel


class RequestCode(BaseModel):
    """Запрос кода авторизации"""

    login: str = "79534499755"
    captcha_id: str | None = None
    captcha_code: str | None = None


class RequestToken(BaseModel):
    """Отправка кода подтверждения"""

    login: str = "79534499755"
    code: str


class CheckToken(BaseModel):
    """Проверка токена авторизации"""

    token: str

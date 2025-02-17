"""
:mod:`helper` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import uuid
from logging import getLogger, Logger

import requests

URL_OPEN = "https://household.key.rt.ru/api/v2/app/devices/30359/open"

URL_AUTH = "https://keyapis.key.rt.ru/identity/api/v1/authorization/send_code"
URL_LOGIN = "https://keyapis.key.rt.ru/identity/api/v1/authorization/login"



__all__ = ("RTHelper",)


class RTHelper:
    """Интрефейс для взаимодействия с API Rt"""

    def __init__(  # noqa: D107
        self,
        mobile_phone: str,
        logger: Logger | None = None,
    ) -> None:
        self.mobile_phone = mobile_phone
        self.headers: dict[str, str] = dict()
        self.logger = logger or getLogger(__name__)

    def auth(self) -> None:
        """Авторизация"""
        x_device_id = str(uuid.uuid4())

        headers = {
            "X-Device-Id": x_device_id,
        }

        payload = {"phoneNumber": self.mobile_phone}
        response = requests.post(URL_AUTH, headers=headers, json=payload)
        self.logger.debug(response.status_code)
        self.logger.debug(response.json())

        code_id = response.json().get("data", {}).get("codeId")

        code = input("Введите код")
        self.logger.debug(code)

        payload = {
            "code": code,
            "codeId": code_id,
        }
        response = requests.post(URL_LOGIN, json=payload, headers=headers)

        self.logger.debug(response.status_code)
        self.logger.debug(response.json())

        token_auth = response.json().get("data", {}).get("accessToken")
        self.logger.debug(token_auth)

        self.headers = {
            "Authorization": token_auth,
        }

    def open_device(self) -> None:
        """Открытие устройства"""
        self.headers = {
            "Authorization": TOKEN,
        }
        response = requests.post(URL_OPEN, headers=self.headers)

        self.logger.debug(response.status_code)
        self.logger.debug(response.text)

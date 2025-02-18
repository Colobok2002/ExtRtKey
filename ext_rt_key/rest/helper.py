"""
:mod:`helper` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import uuid
from dataclasses import dataclass
from logging import getLogger, Logger

import requests

from ext_rt_key.utils.db_helper import DBHelper

URL_OPEN = "https://household.key.rt.ru/api/v2/app/devices/30359/open"

URL_GET_CODE = "https://keyapis.key.rt.ru/identity/api/v1/authorization/send_code"
URL_LOGIN = "https://keyapis.key.rt.ru/identity/api/v1/authorization/login"


# TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6InB1YmxpYzpiNGE4NjgwNC04NDhiLTQzYWQtYmY3Ny01MjI0M2MzZTNhNDEiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOltdLCJjbGllbnRfaWQiOiJiV0Z6ZEdWeU9qa3dOVGszTmpveU1EVTBPVEl3T2pNME9Ub3lPRGczT1RvNk9uUTRhRUpXY3pGdmR5OVBVVlZ1TmpGeVQzWnVLMjFXYldzMVV6UjJLM05CTmpNMFVreERUMVZzWkhjOSIsImV4cCI6MTc3MTMzODI2MSwiZXh0Ijp7fSwiaWF0IjoxNzM5ODAyMjYxLCJpc3MiOiJodHRwczovL29hdXRoMi5rZXkucnQucnUvIiwianRpIjoiMzkwZjBmMmUtOTEwNi00ZTYzLTg2NjEtYWY1ZDAyMWQzOTUxIiwibmJmIjoxNzM5ODAyMjYxLCJzY3AiOltdLCJzdWIiOiJiV0Z6ZEdWeU9qa3dOVGszTmpveU1EVTBPVEl3T2pNME9Ub3lPRGczT1RvNk9uUTRhRUpXY3pGdmR5OVBVVlZ1TmpGeVQzWnVLMjFXYldzMVV6UjJLM05CTmpNMFVreERUMVZzWkhjOSJ9.Tpqlc4ERRpfLfRwu2G7o1DWUufuYjERS7wN7ar40gwiPMJpSq1eawDWzS82zZxs-Ae3_TKKlU5Ri-lY3DelwhVpnngVOV8MvFIG8SQ2xjSENYcAJjFquqyEH2r6m7Uwe9abYQ6njGhzpO3TCbW9UTUo9C5rQYIthi6JfDUSgxpjO0-qb-quOTd_3JCA1ryXiNZlP6bIJM7GR1p_3epifmlvORSnQJKRUMq1a2wuIurJX99VsMSvovULiQ9WTG7NTfYVKrQkscoO0Ip8yQEkYYuB4DYUe_eBLb7JUyu14V3JbxGr2MebaJPj6DYZFOIqgCNxrCQlTo64A4NM4eBLt3ge2PLgdbl7w97g5gn0KXL5G-BB4aQLYhjv1HcweCzAwtClDSABYErKmFHM8bTN_njRFL-vOkiwEs0h__RW8TpCCUVW6qCWAD_G0Gqlmwby6RjxoD7-PYclZs2iNMWbZ41cd02AbbLTRMQl9lyrIyikcnTJBsS1aLTIdd0iTLxwjMtr5zytWpQuVXQuEemRkc0JC1LUYtgxJveoS-yX5Kv_qq1AM6riPiPyAgA8uo7WB-6z5KwY3ffUf5NXxSUvZSIObvOo7iSgPpuvepvH4bzmDFXgxHUxN4yrOL7kNo6uAZmLB0ZIyPQP2aps0A933s-pudKrgSlP8PITUVQoIvws"  # noqa: E501

__all__ = ("RTHelper",)


@dataclass
class AuthSession:
    x_device_id: str | None = None
    code_id: str | None = None
    authorization_token: str | None = None


class AuthManager:
    def __init__(
        self,
        db_helper: DBHelper,
    ) -> None:
        self.session = AuthSession()
        self.db_helper = db_helper

    @property
    def x_device_id(self) -> str | None:
        if self.session.x_device_id is None:
            self.session.x_device_id = str(uuid.uuid4())

        return self.session.x_device_id

    @property
    def code_id(
        self,
    ) -> str | None:
        return self.session.code_id

    @code_id.setter
    def code_id(self, new_code_id: str) -> None:
        self.session.code_id = new_code_id

    @property
    def authorization_token(self) -> str | None:
        return self.session.authorization_token

    @authorization_token.setter
    def authorization_token(self, new_token: str) -> None:
        self.session.authorization_token = new_token

    @property
    def headers_process_auth(self) -> dict[str, str | None]:
        return {
            "X-Device-Id": self.x_device_id,
        }

    @property
    def headers_auth(self) -> dict[str, str | None]:
        return {
            "Authorization": self.authorization_token,
        }


class RTHelper:
    """Интрефейс для взаимодействия с API Rt"""

    def __init__(  # noqa: D107
        self,
        mobile_phone: str,
        db_helper: DBHelper,
        logger: Logger | None = None,
    ) -> None:
        self.mobile_phone = mobile_phone
        self.logger = logger or getLogger(__name__)
        self.auth_manager = AuthManager(db_helper)
        self.db_helper = db_helper

    def requset_token(self, code: str) -> None:
        """Получение токена авторизации"""
        self.logger.debug(f"Запрос токена для {self.mobile_phone}")

        payload = {
            "code": code,
            "codeId": self.auth_manager.session.code_id,
        }

        response = requests.post(
            URL_LOGIN, json=payload, headers=self.auth_manager.headers_process_auth
        )

        self.logger.debug(response.status_code)
        self.logger.debug(response.json())

        token_auth = response.json().get("data", {}).get("accessToken")
        self.logger.debug(token_auth)

    def request_code(self) -> None:
        """Запрос кода авторизации"""
        self.logger.debug(f"Начало авторизации для {self.mobile_phone}")

        payload = {"phoneNumber": self.mobile_phone}

        init_auth_session = requests.post(
            URL_GET_CODE,
            headers=self.auth_manager.headers_process_auth,
            json=payload,
        )

        self.logger.debug(init_auth_session.status_code)
        self.logger.debug(init_auth_session.json())

        # TOOD: Доделать проверку на валидность
        self.auth_manager.code_id = init_auth_session.json().get("data", {}).get("codeId")

    def open_device(self) -> None:
        """Открытие устройства"""
        response = requests.post(URL_OPEN, headers=self.auth_manager.headers_auth)

        self.logger.debug(response.status_code)
        self.logger.debug(response.text)


# rtHelper = RTHelper(mobile_phone="79534499755")

# rtHelper.request_code()

# code = input("Token")

# rtHelper.requset_token(code)

# rtHelper.open_device()

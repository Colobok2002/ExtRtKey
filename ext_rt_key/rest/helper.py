"""
:mod:`helper` -- docs
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import uuid
from dataclasses import dataclass
from http import HTTPStatus
from logging import getLogger, Logger
from typing import Any

import requests

from ext_rt_key.models.db import Login, User
from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.utils.db_helper import DBHelper

URL_GET_CODE = "https://keyapis.key.rt.ru/identity/api/v1/authorization/send_code"
URL_LOGIN = "https://keyapis.key.rt.ru/identity/api/v1/authorization/login"
URL_OPEN = "https://household.key.rt.ru/api/v2/app/devices/30359/open"

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

    def request_token(self, code: str) -> GoodResponse | BadResponse:
        """Получение токена авторизации"""
        self.logger.debug(f"Запрос токена для {self.mobile_phone}")

        payload = {
            "code": code,
            "codeId": self.auth_manager.session.code_id,
        }

        response = requests.post(
            URL_LOGIN, json=payload, headers=self.auth_manager.headers_process_auth
        )

        if response.status_code == HTTPStatus.OK:
            token_auth = response.json().get("data", {}).get("accessToken")
            if token_auth:
                with self.db_helper.sessionmanager() as session:
                    user = (
                        session.query(User)
                        .join(User.logins)
                        .filter(Login.login == self.mobile_phone)
                        .first()
                    )

                    if user:
                        jwt = user.create_token(session=session)
                    else:
                        # TODO: Не срочно сделать так чоб время жизни токена rt сохранялось
                        new_user = User()
                        session.add(new_user)

                        jwt = new_user.create_token(session=session)

                        new_login = Login(
                            login=self.mobile_phone,
                            user=new_user,
                            token=token_auth,
                        )

                        session.add(new_login)
                        session.commit()

                return GoodResponse(
                    message="Токен получен успешно",
                    data={"token": jwt},
                )

        # TODO: Обработка неправильный сообщений по типу не верный код
        print(response.json())
        # input
        # {"error": {"otpCode": {"invalidCode": {}}}}

        # {
        #     "data": {
        #         "accessToken": "...",
        #         "expiredAt": "2026-02-19T20:40:48Z",
        #     }
        # }

        # token_auth = response.json().get("data", {}).get("accessToken")
        # self.logger.info(token_auth)
        return BadResponse()

    def request_code(
        self,
        captcha_id: str | None = None,
        captcha_code: str | None = None,
    ) -> GoodResponse | BadResponse:
        """Запрос кода авторизации"""
        self.logger.info(f"Начало авторизации для {self.mobile_phone}")

        payload: dict[str, Any] = {"phoneNumber": self.mobile_phone}

        if captcha_id and captcha_code:
            payload["captchaAnswer"] = {"id": captcha_id, "code": captcha_code}

        init_auth_session = requests.post(
            URL_GET_CODE,
            headers=self.auth_manager.headers_process_auth,
            json=payload,
        )

        if init_auth_session.status_code == HTTPStatus.OK:
            self.logger.info(init_auth_session.status_code)
            self.logger.info(init_auth_session.json())

            # TODO : Доделать проверку на валидность
            self.auth_manager.code_id = init_auth_session.json().get("data", {}).get("codeId")
            if self.auth_manager.code_id:
                # -> "{data: {codeId: 8tDNvd7m03sKgHvY6XMGJ7HRPn5cRRFMYmmuSTmeH2NTk8SeVSfLhpcWJ2jLUVrHyEmQQN2sVfwOqsfstGy828wO2B4nJbMMd4nh,timeout: 180}}"
                return GoodResponse(message="Код успешно отправлен")

        # INFO: работа с капчей
        if init_auth_session.status_code == HTTPStatus.BAD_REQUEST:
            # ->  {
            #     "error": {
            #         "captchaAnswer": {
            #             "wrongAnswer": {},
            #             "captcha": {
            #                 "id": "c45c6e67-48b0-47fe-8933-d9a4c65f9fbc",
            #                 "url": "https://webapi.passport.rt.ru/captcha/getcaptcha/2.0/c45c6e67-48b0-47fe-8933-d9a4c65f9fbc",
            #             },
            #         }
            #     }
            # }
            response_data = init_auth_session.json()
            if response_data.get("error", {}).get("captchaAnswer"):
                captcha_data = (
                    response_data.get("error", {}).get("captchaAnswer", {}).get("captcha")
                )
                return BadResponse(message="Необходимо пройти капчу", data=captcha_data)

            # -> {"error": {"sso": {"intervalExceeded": {}}}}
            if response_data.get("error", {}).get("sso"):
                return BadResponse(message="Слишком много запросов, немного подождите")
        return BadResponse()

    def open_device(self, rt_token: str) -> GoodResponse | BadResponse:
        """Открытие устройства"""
        self.auth_manager.authorization_token = rt_token + "123"
        response = requests.post(URL_OPEN, headers=self.auth_manager.headers_auth)

        if response.status_code == HTTPStatus.OK:
            return GoodResponse(message="Успешно")

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            # -> {
            #     "error": {
            #         "code": "token_invalid",
            #         "description": "Некорректный токен",
            #         "title": "Некорректный токен",
            #     }
            # }
            # response_data = response.json()
            # Пока так, придумать что делать в этом случае
            return BadResponse(message="Токен устарел, мы работаем над этой проблемой")
        return BadResponse()


# TODO: Следующий шаг подтягивать устройства вот запрос
# await fetch(
#     "https://household.key.rt.ru/api/v2/app/devices/intercom",
#     {
#         "credentials": "include",
#         "headers": {
#             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",
#             "Accept": "application/json, text/plain, */*",
#             "Accept-Language": "ru",
#             "X-Request-Id": "0195202d-c630-7053-91e7-113a2919379b",
#             "Sec-Fetch-Dest": "empty",
#             "Sec-Fetch-Mode": "cors",
#             "Sec-Fetch-Site": "same-site",
#         },
#         "referrer": "https://key.rt.ru/",
#         "method": "GET",
#         "mode": "cors",
#     },
# )
# rtHelper = RTHelper(mobile_phone="79534499755")

# rtHelper.request_code()

# code = input("Token")

# rtHelper.requset_token(code)

# rtHelper.open_device()

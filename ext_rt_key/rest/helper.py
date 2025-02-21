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

from ext_rt_key.models.db import Cameras, Login, User
from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.utils.db_helper import DBHelper

# region AUTH
URL_GET_CODE = "https://keyapis.key.rt.ru/identity/api/v1/authorization/send_code"
URL_LOGIN = "https://keyapis.key.rt.ru/identity/api/v1/authorization/login"
URL_OPEN = "https://household.key.rt.ru/api/v2/app/devices/30359/open"
# endregion

# region DEVISES
URL_GET_ALL_CAMERAS = "https://vc.key.rt.ru/api/v1/cameras?limit=100&offset=0"
URL_GET_INTERCOM = "https://household.key.rt.ru/api/v2/app/devices/intercom"
# URL_OPEN_DEVICE = "https://household.key.rt.ru/api/v2/app/devices/{}/open"
# endregion


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
        db_helper: DBHelper,
        login: str = "79534499755",
        logger: Logger | None = None,
    ) -> None:
        self.login = login
        self.logger = logger or getLogger(__name__)
        self.auth_manager = AuthManager(db_helper)
        self.db_helper = db_helper

        self.init_auth_manager(self.login, self.auth_manager, self.db_helper)

    @staticmethod
    def init_auth_manager(
        login: str,
        auth_manager: AuthManager,
        db_helper: DBHelper,
    ) -> None:
        """Инициализация менеджера авторизации при инициализации класса"""
        with db_helper.sessionmanager() as session:
            login_model = session.query(Login).filter(Login.login == login).first()
            if not login_model:
                return None
            auth_manager.authorization_token = login_model.token

    async def request_token(self, code: str) -> GoodResponse | BadResponse:
        """Получение токена авторизации"""
        self.logger.debug(f"Запрос токена для {self.login}")

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
                        .filter(Login.login == self.login)
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
                            login=self.login,
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
        # print(response.json())
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

    async def request_code(
        self,
        captcha_id: str | None = None,
        captcha_code: str | None = None,
    ) -> GoodResponse | BadResponse:
        """Запрос кода авторизации"""
        self.logger.info(f"Начало авторизации для {self.login}")

        payload: dict[str, Any] = {"phoneNumber": self.login}

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
                return GoodResponse(message="На ваше устройство отправлен код")

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

    async def open_device(
        self,
    ) -> GoodResponse | BadResponse:
        """Открытие устройства"""
        return await self.get_cameras()
        # self.auth_manager.authorization_token = rt_token
        # response = requests.post(URL_OPEN, headers=self.auth_manager.headers_auth)

        # if response.status_code == HTTPStatus.OK:
        #     return GoodResponse(message="Успешно")

        # if response.status_code == HTTPStatus.UNAUTHORIZED:
        #     # -> {
        #     #     "error": {
        #     #         "code": "token_invalid",
        #     #         "description": "Некорректный токен",
        #     #         "title": "Некорректный токен",
        #     #     }
        #     # }
        #     # response_data = response.json()
        #     # Пока так, придумать что делать в этом случае
        #     return BadResponse(message="Токен устарел, мы работаем над этой проблемой")
        return BadResponse()

    async def get_cameras(self) -> GoodResponse | BadResponse:
        """Выгрузка в базу всех камер"""
        response = requests.get(
            URL_GET_ALL_CAMERAS,
            headers=self.auth_manager.headers_auth,
        )

        if response.status_code == HTTPStatus.OK:
            response_data = response.json().get("data").get("items")

            with self.db_helper.sessionmanager() as session:
                for camera in response_data:
                    id_ = camera.get("id", {})
                    camera_model = session.query(Cameras).filter(Cameras.rt_id == id_).first()

                    if camera_model:
                        camera_model.archive_length = camera.get("archive_length")
                        camera_model.screenshot_url_template = camera.get("screenshot_url_template")
                        camera_model.screenshot_token = camera.get("screenshot_token")
                        camera_model.streamer_token = camera.get("streamer_token", {})

                    else:
                        new_camera = Cameras(
                            archive_length=camera.get("archive_length"),
                            rt_id=id_,
                            screenshot_url_template=camera.get("screenshot_url_template"),
                            screenshot_token=camera.get("screenshot_token"),
                            streamer_token=camera.get("streamer_token", {}),
                            login=self.login,
                        )
                        session.add(new_camera)
                session.commit()

            return GoodResponse(message="Данные камер успешно обновлены")

        return BadResponse(message="")


#     def _get_intercom(self, rt_token: str) -> None:
#         self.auth_manager.authorization_token = rt_token
#         response = requests.get(URL_GET_INTERCOM, headers=self.auth_manager.headers_auth)
#         if response.status_code == HTTPStatus.OK:
#             intercoms = response.json().get("data", {}).get("devices", [])
#             for intercom in intercoms:
#                 print(intercom)
#             {
#                 "data": {
#                     "devices": [
#                         {
#                             "id": "30369",
#                             "device_type": "intercom",
#                             "serial_number": "264616",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "camera_id": "da86406e-e2e7-47e7-b5c3-49335d507844",
#                             "description": "калитка под3",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "калитка под3",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "temporary_key", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "sip_calls", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "dtmf_code", "setup": True},
#                                 {"name": "sip_video", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "emergency_door", "setup": True},
#                                 {"name": "gate", "setup": True},
#                                 {"name": "flat_autocollect", "setup": True},
#                                 {"name": "face_recognition", "setup": False},
#                                 {"name": "autocollect", "setup": True},
#                                 {"name": "change_password", "setup": True},
#                                 {"name": "cms_phones", "setup": False},
#                                 {"name": "reinstall", "setup": True},
#                                 {"name": "emergency_call", "setup": True},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                         {
#                             "id": "30368",
#                             "device_type": "intercom",
#                             "serial_number": "FC7D004845",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "description": "Калитка 6",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "Калитка 6",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "sl3", "setup": False},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                         {
#                             "id": "30367",
#                             "device_type": "intercom",
#                             "serial_number": "FC7D004614",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "description": "Подвал 6",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "Подвал 6",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "sl3", "setup": False},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                         {
#                             "id": "30353",
#                             "device_type": "intercom",
#                             "serial_number": "217841",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "camera_id": "cb844197-a935-4b78-90a5-16468d043be1",
#                             "description": "подьезд№6",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "подьезд№6",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "temporary_key", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "sip_calls", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "dtmf_code", "setup": True},
#                                 {"name": "sip_video", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "emergency_door", "setup": True},
#                                 {"name": "gate", "setup": True},
#                                 {"name": "flat_autocollect", "setup": True},
#                                 {"name": "face_recognition", "setup": False},
#                                 {"name": "autocollect", "setup": True},
#                                 {"name": "change_password", "setup": True},
#                                 {"name": "cms_phones", "setup": False},
#                                 {"name": "reinstall", "setup": True},
#                                 {"name": "emergency_call", "setup": True},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                         {
#                             "id": "30342",
#                             "device_type": "intercom",
#                             "serial_number": "263112",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "camera_id": "b1b4e9c6-3182-4a06-98c3-8da3c474148f",
#                             "description": "калитка 5под",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "калитка 5под",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "temporary_key", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "sip_calls", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "dtmf_code", "setup": True},
#                                 {"name": "sip_video", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "emergency_door", "setup": True},
#                                 {"name": "gate", "setup": True},
#                                 {"name": "flat_autocollect", "setup": True},
#                                 {"name": "face_recognition", "setup": False},
#                                 {"name": "autocollect", "setup": True},
#                                 {"name": "change_password", "setup": True},
#                                 {"name": "cms_phones", "setup": False},
#                                 {"name": "reinstall", "setup": True},
#                                 {"name": "emergency_call", "setup": True},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                         {
#                             "id": "30341",
#                             "device_type": "intercom",
#                             "serial_number": "218278",
#                             "device_group": ["Калитка"],
#                             "utc_offset_minutes": 180,
#                             "camera_id": "b1b4e9c6-3182-4a06-98c3-8da3c474148f",
#                             "description": "калитка 1под",
#                             "is_favorite": False,
#                             "is_active": True,
#                             "name_by_company": "калитка 1под",
#                             "name_by_user": None,
#                             "accept_concierge_call": False,
#                             "capabilities": [
#                                 {"name": "temporary_key", "setup": True},
#                                 {"name": "constant_key", "setup": True},
#                                 {"name": "sip_calls", "setup": True},
#                                 {"name": "open_door", "setup": True},
#                                 {"name": "dtmf_code", "setup": True},
#                                 {"name": "sip_video", "setup": True},
#                                 {"name": "ntp", "setup": True},
#                                 {"name": "syslog", "setup": True},
#                                 {"name": "emergency_door", "setup": True},
#                                 {"name": "gate", "setup": True},
#                                 {"name": "flat_autocollect", "setup": True},
#                                 {"name": "face_recognition", "setup": False},
#                                 {"name": "autocollect", "setup": True},
#                                 {"name": "change_password", "setup": True},
#                                 {"name": "cms_phones", "setup": False},
#                                 {"name": "reinstall", "setup": True},
#                                 {"name": "emergency_call", "setup": True},
#                             ],
#                             "inter_codes": [
#                                 {
#                                     "id": 11769328,
#                                     "code": "045F89A2FF7580",
#                                     "start_date": "2024-11-28T10:57:45.976829Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                 },
#                                 {
#                                     "id": 12324802,
#                                     "code": "047822CAFF7580",
#                                     "start_date": "2024-12-25T10:32:39.125167Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                                 {
#                                     "id": 12324803,
#                                     "code": "042D6ED2FF7580",
#                                     "start_date": "2024-12-25T10:32:39.228528Z",
#                                     "end_date": None,
#                                     "inter_code_type": "constant",
#                                     "description": "",
#                                 },
#                             ],
#                         },
#                     ]
#                 }
#             }


# # TODO: Следующий шаг подтягивать устройства вот запрос
# # await fetch(
# #     "https://household.key.rt.ru/api/v2/app/devices/intercom",
# #     {
# #         "credentials": "include",
# #         "headers": {
# #             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) Gecko/20100101 Firefox/135.0",  # noqa
# #             "Accept": "application/json, text/plain, */*",
# #             "Accept-Language": "ru",
# #             "X-Request-Id": "0195202d-c630-7053-91e7-113a2919379b",
# #             "Sec-Fetch-Dest": "empty",
# #             "Sec-Fetch-Mode": "cors",
# #             "Sec-Fetch-Site": "same-site",
# #         },
# #         "referrer": "https://key.rt.ru/",
# #         "method": "GET",
# #         "mode": "cors",
# #     },
# # )
# # rtHelper = RTHelper(mobile_phone="79534499755")

# # rtHelper.request_code()

# # code = input("Token")

# # rtHelper.requset_token(code)

# # rtHelper.open_device()

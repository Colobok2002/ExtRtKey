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
from sqlalchemy import and_

from ext_rt_key.models.db import Cameras, Devices, DeviceType, Login, User
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
URL_GET_BARRIER = "https://household.key.rt.ru/api/v2/app/devices/barrier"
URL_OPEN_DEVICE = "https://household.key.rt.ru/api/v2/app/devices/{}/open"
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

    def __init__(
        self,
        db_helper: DBHelper,
        login: str = "79534499755",
        logger: Logger | None = None,
    ) -> None:
        """
        Init метод

        :param db_helper: _description_
        :type db_helper: _type_
        :param login: _description_, defaults to "79534499755"
        :type login: _type_, optional
        :param logger: _description_, defaults to None
        :type logger: _type_, optional
        """
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
                # -> "{data: {codeId: 8tDNvd7m03sKgHvY6XMGJ7HRPn5cRRFMYmmuSTmeH2NTk8SeVSfLhpcWJ2jLUVrHyEmQQN2sVfwOqsfstGy828wO2B4nJbMMd4nh,timeout: 180}}"  # noqa
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

    async def load_devices(self) -> GoodResponse | BadResponse:
        """Загрузка всех устройств"""
        status_dict: dict[str, bool] = {}
        status_dict["CAMERAS"] = isinstance(await self.get_cameras(), GoodResponse)
        status_dict["INTERCOM"] = isinstance(
            await self._get_devices(URL_GET_INTERCOM), GoodResponse
        )
        status_dict["BARRIER"] = isinstance(await self._get_devices(URL_GET_BARRIER), GoodResponse)

        return GoodResponse(
            message="Данные успешно обновлены",
            data=status_dict,
        )

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

    async def _get_devices(
        self,
        target_url: str,
    ) -> GoodResponse | BadResponse:
        """Выгрузка домофонов"""
        # Актуализируем камеры
        await self.get_cameras()
        response = requests.get(target_url, headers=self.auth_manager.headers_auth)
        if response.status_code == HTTPStatus.OK:
            intercoms = response.json().get("data", {}).get("devices", [])
            with self.db_helper.sessionmanager() as session:
                for intercom in intercoms:
                    intercom_model = (
                        session.query(Devices)
                        .filter(
                            and_(
                                Devices.rt_id == intercom.get("id"),
                                Devices.login_id == self.login,
                            )
                        )
                        .first()
                    )
                    if intercom_model:
                        intercom_model.description = intercom.get("description")
                        # Добавляем в избранное ток если новое пришло True а тут False
                        if not intercom_model.is_favorite and intercom.get("is_favorite"):
                            intercom_model.is_favorite = intercom.get("is_favorite")
                    else:
                        intercom_model = Devices(
                            rt_id=intercom.get("id"),
                            device_type=DeviceType(intercom.get("device_type")),
                            login_id=self.login,
                            camera_id=intercom.get("camera_id"),
                            description=intercom.get("description"),
                            is_favorite=intercom.get("is_favorite"),
                            name_by_user=intercom.get("name_by_user"),
                        )

                        session.add(intercom_model)
                session.commit()
            return GoodResponse(message="Данные домофонов успешно обновлены")

        return GoodResponse()

    async def open_device(
        self,
    ) -> GoodResponse | BadResponse:
        """Открытие устройства"""
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

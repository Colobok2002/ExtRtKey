"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.models.db import Login
from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.common import RoutsCommon

__all__ = ("AuthRouter",)


class AuthRouter(RoutsCommon):
    """Роутер для авторизации"""

    def setup_routes(self) -> None:
        """Функция назначения routs"""
        self._router.add_api_route("/request_code", self.request_code, methods=["POST"])
        self._router.add_api_route("/request_token", self.request_token, methods=["POST"])
        self._router.add_api_route("/open_dor", self.open_dor, methods=["POST"])

    async def request_code(
        self,
        mobile_phone: str = "79534499755",
        captcha_id: str | None = None,
        captcha_code: str | None = None,
    ) -> GoodResponse | BadResponse:
        """Запрос кода авторизации"""
        rt_helper = self.rt_manger.add_helper(mobile_phone)
        return rt_helper.request_code(
            captcha_id=captcha_id,
            captcha_code=captcha_code,
        )

    async def request_token(
        self,
        mobile_phone: str,
        code: str,
    ) -> GoodResponse | BadResponse:
        """Получение токена авторизации"""
        rt_helper = self.rt_manger.get_helpers(mobile_phone)

        if rt_helper:
            self.logger.info("Токен успешно получен")
            return rt_helper.request_token(code)

        self.logger.info("Сессия не найдена")
        return self.bad_response("Сессия не найдена")

    async def open_dor(
        self,
        mobile_phone: str,
        # jwt: str,
    ) -> GoodResponse | BadResponse:
        """
        Открытие устройство
        На данном этапе 1 конкретного
        """
        # TODO: Пока временный метод для разработки
        # В будующем в базе будут хранится устройство и login
        # Проверяем что владелец jwt имеет доступ к этому методу пока проверку пропустим

        with self.db_helper.sessionmanager() as session:
            login = session.query(Login).filter(Login.login == mobile_phone).first()
            print(login)
            if not login:
                return self.bad_response("Ваше сессия завершена")
            rt_key = login.token

        rt_helper = self.rt_manger.add_helper(mobile_phone)

        if rt_helper:
            self.logger.info("Устройство открыто")
            return rt_helper.open_device(rt_key)

        self.logger.info("Сессия не найдена")
        return self.bad_response()

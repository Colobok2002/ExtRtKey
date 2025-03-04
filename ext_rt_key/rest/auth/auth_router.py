"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.common import RoutsCommon

__all__ = ("AuthRouter",)


class AuthRouter(RoutsCommon):
    """Роутер для авторизации"""

    def setup_routes(self) -> None:
        """Функция назначения routs"""
        self._router.add_api_route("/request_code", self.request_code, methods=["POST"])
        self._router.add_api_route("/request_token", self.request_token, methods=["POST"])

    async def request_code(
        self,
        login: str = "79534499755",
        captcha_id: str | None = None,
        captcha_code: str | None = None,
    ) -> GoodResponse | BadResponse:
        """Запрос кода авторизации"""
        rt_helper = self.rt_manger.add_helper(login)
        return await rt_helper.request_code(
            captcha_id=captcha_id,
            captcha_code=captcha_code,
        )

    async def request_token(
        self,
        login: str,
        code: str,
    ) -> GoodResponse | BadResponse:
        """Получение токена авторизации"""
        rt_helper = self.rt_manger.get_helpers(login)

        if rt_helper:
            self.logger.info("Токен успешно получен")
            return await rt_helper.request_token(code)

        self.logger.info("Сессия не найдена")
        return self.bad_response("Сессия не найдена")

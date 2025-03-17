"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.auth.models import CheckToken, RequestCode, RequestToken
from ext_rt_key.rest.common import RoutsCommon

__all__ = ("AuthRouter",)


class AuthRouter(RoutsCommon):
    """Роутер для авторизации"""

    def setup_routes(self) -> None:
        """Функция назначения routs"""
        self._router.add_api_route("/request_code", self.request_code, methods=["POST"])
        self._router.add_api_route("/request_token", self.request_token, methods=["POST"])
        self._router.add_api_route("/check_token", self.check_token, methods=["POST"])

    async def request_code(
        self,
        data: RequestCode,
    ) -> GoodResponse | BadResponse:
        """Запрос кода авторизации"""
        rt_helper = self.rt_manger.add_helper(data.login)
        return await rt_helper.request_code(
            captcha_id=data.captcha_id,
            captcha_code=data.captcha_code,
        )

    async def request_token(
        self,
        data: RequestToken,
    ) -> GoodResponse | BadResponse:
        """Получение токена авторизации"""
        rt_helper = self.rt_manger.get_helpers(data.login)

        if rt_helper:
            self.logger.info("Токен успешно получен")
            return await rt_helper.request_token(data.code)

        self.logger.info("Сессия не найдена")
        return self.bad_response("Сессия не найдена")

    async def check_token(
        self,
        data: CheckToken,
    ) -> GoodResponse | BadResponse:
        """Проверка токена авторизации"""
        with self.db_helper.sessionmanager() as session:
            user = (
                session.query(self.models.User)
                .filter(self.models.User.jwt_token == data.token)
                .first()
            )
            if user:
                if user.verify_token() is None:
                    return self.bad_response("Не валидный токен")
                return self.good_response()

        return self.bad_response("Не валидный токен")

"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.rest.common import RoutsCommon

__all__ = ("AuthRouter",)


class AuthRouter(RoutsCommon):
    """Роутер для авторизации"""

    def setup_routes(self) -> None:
        """Функция назначения routs"""
        self._router.add_api_route("/pong", self.pong, methods=["GET"])

    async def pong(self) -> dict[str, str]:
        "Ping pong"
        self.logger.info("Pogn result", extra={"data": "pong"})
        return {"data": "pong"}

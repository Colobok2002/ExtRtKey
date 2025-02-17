"""
:mod:`app` -- Demo Rest API
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.rest.common import RoutsCommon


class PingRouter(RoutsCommon):
    """Класс для создания и запуска Rest API"""

    def setup_routes(self) -> None:
        self._router.add_api_route("/pong", self.pong, methods=["GET"])

    async def pong(self) -> dict[str, str]:
        self.logger.info("Pogn result", extra={"data": "pong"})
        return {"data": "pong"}

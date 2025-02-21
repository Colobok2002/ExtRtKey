"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.common import RoutsCommon

__all__ = ("DevicesRouter",)


class DevicesRouter(RoutsCommon):
    """Роутер для авторизации и видео трансляции"""

    def setup_routes(self) -> None:
        """Функция назначения маршрутов"""
        self._router.add_api_route("/load_devices", self.load_devices, methods=["POST"])

    async def load_devices(
        self,
        login: str,
        # jwt: str,
    ) -> GoodResponse | BadResponse:
        """
        Открытие устройство
        На данном этапе 1 конкретного
        """
        # TODO: Пока временный метод для разработки
        # В будующем в базе будут хранится устройство и login
        # Проверяем что владелец jwt имеет доступ к этому методу пока проверку пропустим

        rt_helper = self.rt_manger.add_helper(login)

        if rt_helper:
            self.logger.info("Начало выгрузки устройств для", extra={"login": login})
            return await rt_helper.load_devices()

        self.logger.info("Сессия не найдена")
        return self.bad_response()

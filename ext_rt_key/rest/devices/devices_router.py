"""
:mod:`AuthRouter` -- Роутер для авторизации
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from ext_rt_key.models.request import BadResponse, GoodResponse
from ext_rt_key.rest.common import RoutsCommon
from ext_rt_key.rest.devices.models import LoadDevices

__all__ = ("DevicesRouter",)


class DevicesRouter(RoutsCommon):
    """Роутер для авторизации и видео трансляции"""

    def setup_routes(self) -> None:
        """Функция назначения маршрутов"""
        self._router.add_api_route("/load_devices", self.load_devices, methods=["POST"])
        self._router.add_api_route("/get_cameras", self.get_cameras, methods=["GET"])
        self._router.add_api_route("/get_intercom", self.get_intercom, methods=["GET"])
        self._router.add_api_route("/get_barrier", self.get_barrier, methods=["GET"])

    async def load_devices(
        self,
        data: LoadDevices,
    ) -> GoodResponse | BadResponse:
        """Выгрузка всех устройств с Rt"""
        if self.access_check(jwt_token=data.token, login_id=data.login_id) is False:
            return self.bad_response(message="Недостаточно прав")

        login = self.get_user_login(data.login_id)
        if not login:
            return self.bad_response(message="Не найдены данные авторизации")

        rt_helper = self.rt_manger.add_helper(login)

        if rt_helper:
            self.logger.info("Начало выгрузки устройств для", extra={"login": login})
            return await rt_helper.load_devices()

        return self.bad_response()

    async def get_cameras(
        self,
        jwt_token: str,
        login_id: int,
    ) -> GoodResponse | BadResponse:
        """Получение списка камер"""
        if (
            self.access_check(
                jwt_token=jwt_token,
                login_id=login_id,
            )
            is False
        ):
            return self.bad_response(message="Недостаточно прав")

        with self.db_helper.sessionmanager() as session:
            login_model = session.query(self.models.Login).get(login_id)
            return self.good_response(data={"cameras": login_model.all_cameras})

        return self.bad_response()

    async def get_intercom(
        self,
        jwt_token: str,
        login_id: int,
    ) -> GoodResponse | BadResponse:
        """Получение списка шлагбаумов/ворот"""
        if (
            self.access_check(
                jwt_token=jwt_token,
                login_id=login_id,
            )
            is False
        ):
            return self.bad_response(message="Недостаточно прав")

        with self.db_helper.sessionmanager() as session:
            login_model = session.query(self.models.Login).get(login_id)
            return self.good_response(data={"intercom": login_model.intercom})

        return self.bad_response()

    async def get_barrier(
        self,
        jwt_token: str,
        login_id: int,
    ) -> GoodResponse | BadResponse:
        """Получение списка домофонов и камер при наличии"""
        if (
            self.access_check(
                jwt_token=jwt_token,
                login_id=login_id,
            )
            is False
        ):
            return self.bad_response(message="Недостаточно прав")

        with self.db_helper.sessionmanager() as session:
            login_model = session.query(self.models.Login).get(login_id)
            return self.good_response(data={"barrier": login_model.barrier})

        return self.bad_response()

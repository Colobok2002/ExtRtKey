"""
:mod:`manager` -- Менеджер по работе с Rt
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

from logging import getLogger, Logger

from ext_rt_key.rest.helper import RTHelper
from ext_rt_key.utils.db_helper import DBHelper


class RTManger:
    """Менеджер по работе с Rt Helpers"""

    def __init__(  # noqa: D107
        self,
        db_helper: DBHelper,
        logger: Logger | None = None,
    ) -> None:
        self.logger = logger or getLogger(__name__)

        # TODO: На будущее чтоб работать с несколькими ключами
        # self.helpers: dict[str, list[RTHelper]] = dict()
        self.helpers: dict[str, RTHelper] = dict()
        self.db_helper = db_helper

    def add_helper(self, login: str) -> RTHelper:
        """
        Добавление хелпера для номера телефона

        :param login: Логин str
        :return: None
        """
        if login in self.helpers:
            self.logger.info(f"RTHelper для {login} уже есть")
            return self.helpers[login]

        self.helpers[login] = RTHelper(
            login=login,
            logger=self.logger,
            db_helper=self.db_helper,
        )

        return self.helpers[login]

    def get_helpers(self, login: str) -> RTHelper | None:
        """
        Возвращает все хелперы для номера телефона

        :param login: Логин
        :return: list[RTHelper]
        """
        return self.helpers.get(login, None)

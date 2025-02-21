"""
:mod:`db` -- Модели для работы с базойА
===================================
.. moduleauthor:: ilya Barinov <i-barinov@it-serv.ru>
"""

import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

from ext_rt_key.utils.jwt_helper import JWTHelper


class Base(DeclarativeBase):
    """Базовый класс для моделей"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pass


class User(Base):
    """Таблица с пользователями"""

    __tablename__ = "user"

    secret_key: Mapped[str] = mapped_column(String)
    jwt_token: Mapped[str] = mapped_column(String)

    logins: Mapped[list["Login"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def create_token(self, session: Session) -> str:
        """
        Создание JWT токена

        :return: токен
        """
        if self.secret_key is None:
            self.secret_key = JWTHelper.generate_secure_jwt_key()

        token = JWTHelper.create_token(
            {"user_id": self.id},
            key=self.secret_key,
        )
        self.jwt_token = token

        session.commit()

        return token

    def verify_token(self) -> dict[str, Any] | None:
        """Верификация токена"""
        return JWTHelper.verify_token(token=self.jwt_token, key=self.secret_key)

    # Отдельный метод чтоб не было путаницы
    get_payload = verify_token


class Login(Base):
    """Таблица с номерами телефонов"""

    __tablename__ = "Login"

    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )

    token: Mapped[str] = mapped_column(String, unique=True)

    expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    address: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="logins")

    def is_expired(self) -> bool:
        """Проверяет, истёк ли токен"""
        if self.expires_at:
            return datetime.datetime.now(datetime.UTC) > self.expires_at
        return True


class Cameras(Base):
    # medium
    __tablename__ = "cameras"

    archive_length: Mapped[int] = mapped_column(Integer, doc="Количество архивных дней")
    rt_id: Mapped[str] = mapped_column(String, doc="Id в системе rt")
    screenshot_url_template: Mapped[str] = mapped_column(
        String, doc="Шаблон Url для получения снимка"
    )
    screenshot_token: Mapped[str] = mapped_column(String, doc="Токен для получения скриншота")
    streamer_token: Mapped[str] = mapped_column(String, doc="Токен для получения видео трансляции")

    login: Mapped[str] = mapped_column(
        String, ForeignKey("Login.login", ondelete="CASCADE"), nullable=False
    )


# "https://media-vdk4.camera.rt.ru/image/{size}/4e55bb9a-58e9-49c9-a790-f52b8eea8687/{timestamp}.jpg?token={cdn_token}

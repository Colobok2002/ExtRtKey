import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для моделей"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pass


class PhoneNumber(Base):
    """Таблица с номерами телефонов"""

    __tablename__ = "phone_numbers"

    phone: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)

    tokens: Mapped[list["Token"]] = relationship(
        back_populates="phone_number", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PhoneNumber(id={self.id}, phone={self.phone})>"


class Token(Base):
    """Таблица с токенами"""

    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))

    phone_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("phone_numbers.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    # Связь с номером телефона
    phone_number: Mapped["PhoneNumber"] = relationship(back_populates="tokens")

    def is_expired(self) -> bool:
        """Проверяет, истёк ли токен"""
        return datetime.datetime.now(datetime.UTC) > self.expires_at

    def __repr__(self) -> str:
        return f"<Token(id={self.id}, token={self.token}, phone_id={self.phone_id}, expires_at={self.expires_at})>"

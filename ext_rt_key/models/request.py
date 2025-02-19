from typing import Any

from pydantic import BaseModel, Field


class Response(BaseModel):
    """Базовый класс для ответов"""

    status: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None


class BadResponse(Response):
    """Класс плохого ответа"""

    status: str = Field(default="Bad", init=False)


class GoodResponse(Response):
    """Класс хорошего ответа"""

    status: str = Field(default="Good", init=False)

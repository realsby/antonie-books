from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=200)]
Tag = Annotated[str, Field(min_length=1, max_length=50)]


class BookIn(BaseModel):
    """Body for POST /books. The server sets created_at and updated_at."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(ge=1)
    title: Text
    publisher: Text
    author: Text
    pages: int = Field(gt=0, le=100_000)
    tags: list[Tag] = Field(default=[], max_length=20)


class BookUpdate(BaseModel):
    """Body for PATCH /books/{id}. Send only the fields you want to change."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Text | None = None
    publisher: Text | None = None
    author: Text | None = None
    pages: int | None = Field(default=None, gt=0, le=100_000)
    tags: list[Tag] | None = Field(default=None, max_length=20)


class Book(BaseModel):
    id: int
    title: str
    publisher: str
    author: str
    pages: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class BookPage(BaseModel):
    items: list[Book]
    page: int
    limit: int
    total: int

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Id = Annotated[int, Field(ge=1)]

Text = Annotated[str, Field(min_length=1, max_length=200)]
Tag = Annotated[str, Field(min_length=1, max_length=50)]


def split_names(text: str) -> list[str]:
    # "Harry Percival, Bob Gregory" -> ["Harry Percival", "Bob Gregory"]
    names = [name.strip() for name in text.split(",")]
    return [name for name in names if name]


def check_names(text: str | None) -> str | None:
    if text is not None and not split_names(text):
        raise ValueError("author must have at least one name")
    return text


def check_birth_date(value: date | None) -> date | None:
    if value and value > date.today():
        raise ValueError("birth_date can not be in the future")
    return value


class BookIn(BaseModel):
    """Body for POST /books.

    Send the authors as names ("author") or as ids ("author_ids"), not both.
    The server sets created_at and updated_at.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: Id
    title: Text
    publisher: Text
    author: Text | None = None
    author_ids: list[Id] | None = Field(default=None, min_length=1, max_length=20)
    pages: int = Field(gt=0, le=100_000)
    tags: list[Tag] = Field(default=[], max_length=20)

    @field_validator("author")
    @classmethod
    def check_author(cls, value: str | None) -> str | None:
        return check_names(value)

    @model_validator(mode="after")
    def author_or_ids(self):
        if (self.author is None) == (self.author_ids is None):
            raise ValueError("send author or author_ids, but not both")
        return self


class BookUpdate(BaseModel):
    """Body for PATCH /books/{id}. Send only the fields you want to change."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Text | None = None
    publisher: Text | None = None
    author: Text | None = None
    author_ids: list[Id] | None = Field(default=None, min_length=1, max_length=20)
    pages: int | None = Field(default=None, gt=0, le=100_000)
    tags: list[Tag] | None = Field(default=None, max_length=20)

    @field_validator("author")
    @classmethod
    def check_author(cls, value: str | None) -> str | None:
        return check_names(value)

    @model_validator(mode="after")
    def not_both(self):
        if self.author is not None and self.author_ids is not None:
            raise ValueError("send author or author_ids, but not both")
        return self


class Book(BaseModel):
    id: int
    title: str
    publisher: str
    author: str
    pages: int
    tags: list[str]
    author_ids: list[int]
    created_at: datetime
    updated_at: datetime


class BookPage(BaseModel):
    items: list[Book]
    page: int
    limit: int
    total: int


class AuthorIn(BaseModel):
    """Body for POST /authors. Two authors can have the same name."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Text
    birth_date: date | None = None

    @field_validator("name")
    @classmethod
    def no_comma(cls, value: str) -> str:
        # Books use a comma between author names, so a name can not have one.
        if "," in value:
            raise ValueError("name can not have a comma")
        return value

    @field_validator("birth_date")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        return check_birth_date(value)


class AuthorUpdate(BaseModel):
    """Body for PATCH /authors/{id}. Only birth_date can change, because books use the name."""

    birth_date: date | None

    @field_validator("birth_date")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        return check_birth_date(value)


class Author(BaseModel):
    id: int
    name: str
    birth_date: date | None = None


class AuthorWithCount(Author):
    book_count: int

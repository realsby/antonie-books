from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.models import AuthorIn, AuthorUpdate, BookIn, BookUpdate, split_names

GOOD_BOOK = {
    "id": 1,
    "title": "Learning Python",
    "publisher": "O'Reilly Media",
    "author": "Mark Lutz",
    "pages": 1648,
    "tags": ["Python"],
}


def test_split_names():
    assert split_names("Harry Percival, Bob Gregory") == ["Harry Percival", "Bob Gregory"]
    assert split_names(" Mark Lutz ") == ["Mark Lutz"]
    assert split_names("a,,b,") == ["a", "b"]
    assert split_names(" , ") == []


def test_book_is_valid():
    book = BookIn(**GOOD_BOOK)
    assert book.title == "Learning Python"


def test_book_removes_spaces():
    book = BookIn(**{**GOOD_BOOK, "title": "  Learning Python  "})
    assert book.title == "Learning Python"


def test_book_with_author_ids():
    data = {**GOOD_BOOK, "author_ids": [1, 2]}
    del data["author"]
    assert BookIn(**data).author_ids == [1, 2]


def test_book_needs_author_or_ids():
    data = {**GOOD_BOOK}
    del data["author"]
    with pytest.raises(ValidationError):
        BookIn(**data)
    with pytest.raises(ValidationError):
        BookIn(**{**GOOD_BOOK, "author_ids": [1]})


@pytest.mark.parametrize("ids", [[], [0], ["abc"], [1] * 21])
def test_book_bad_author_ids(ids):
    data = {**GOOD_BOOK, "author_ids": ids}
    del data["author"]
    with pytest.raises(ValidationError):
        BookIn(**data)


def test_book_tags_are_optional():
    data = {**GOOD_BOOK}
    del data["tags"]
    assert BookIn(**data).tags == []


def test_book_ignores_server_fields():
    # The sample data has created_at. The server sets it, so we ignore it.
    book = BookIn(**{**GOOD_BOOK, "created_at": "2017-01-12T00:00:00+03:00"})
    assert "created_at" not in book.model_dump()


@pytest.mark.parametrize(
    "field, value",
    [
        ("id", 0),
        ("id", "abc"),
        ("title", ""),
        ("title", "x" * 201),
        ("publisher", "   "),
        ("author", " , "),
        ("pages", 0),
        ("pages", 1.5),
        ("pages", 100_001),
        ("tags", "Python"),
        ("tags", [""]),
        ("tags", ["x"] * 21),
    ],
)
def test_book_bad_values(field, value):
    with pytest.raises(ValidationError):
        BookIn(**{**GOOD_BOOK, field: value})


@pytest.mark.parametrize("field", ["id", "title", "publisher", "author", "pages"])
def test_book_needs_field(field):
    data = {**GOOD_BOOK}
    del data[field]
    with pytest.raises(ValidationError):
        BookIn(**data)


def test_update_keeps_only_sent_fields():
    update = BookUpdate(pages=10)
    assert update.model_dump(exclude_none=True) == {"pages": 10}


def test_update_bad_values():
    with pytest.raises(ValidationError):
        BookUpdate(pages=-5)
    with pytest.raises(ValidationError):
        BookUpdate(author=",")
    with pytest.raises(ValidationError):
        BookUpdate(author="Mark Lutz", author_ids=[1])


def test_new_author():
    author = AuthorIn(name="  John Smith ", birth_date="1970-01-01")
    assert author.name == "John Smith"
    assert AuthorIn(name="John Smith").birth_date is None


@pytest.mark.parametrize("name", ["", "   ", "Smith, John", "x" * 201])
def test_new_author_bad_name(name):
    with pytest.raises(ValidationError):
        AuthorIn(name=name)


def test_author_birth_date():
    assert AuthorUpdate(birth_date="1960-05-30").birth_date == date(1960, 5, 30)
    assert AuthorUpdate(birth_date=None).birth_date is None


def test_author_birth_date_not_in_future():
    tomorrow = date.today() + timedelta(days=1)
    with pytest.raises(ValidationError):
        AuthorUpdate(birth_date=tomorrow)
    with pytest.raises(ValidationError):
        AuthorIn(name="John Smith", birth_date=tomorrow)

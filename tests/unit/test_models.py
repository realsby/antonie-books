import pytest
from pydantic import ValidationError

from app.models import BookIn, BookUpdate

GOOD_BOOK = {
    "id": 1,
    "title": "Learning Python",
    "publisher": "O'Reilly Media",
    "author": "Mark Lutz",
    "pages": 1648,
    "tags": ["Python"],
}


def test_book_is_valid():
    book = BookIn(**GOOD_BOOK)
    assert book.title == "Learning Python"


def test_book_removes_spaces():
    book = BookIn(**{**GOOD_BOOK, "title": "  Learning Python  "})
    assert book.title == "Learning Python"


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

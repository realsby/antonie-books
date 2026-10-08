import re
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.authors import link_authors
from app.db import DB, NO_ID
from app.models import Book, BookIn, BookPage, BookUpdate, PathId

router = APIRouter(prefix="/books", tags=["books"])


def contains(text: str) -> re.Pattern:
    # re.escape stops users from sending their own regex. Case does not matter.
    return re.compile(re.escape(text), re.IGNORECASE)


def exact(text: str) -> re.Pattern:
    return re.compile(f"^{re.escape(text)}$", re.IGNORECASE)


def make_filter(author: str | None, title: str | None, tags: str | None) -> dict:
    query = {}
    if author:
        query["author"] = contains(author)
    if title:
        query["title"] = contains(title)
    if tags:
        # tags=Python,Learning -> the book must have both tags.
        names = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if names:
            query["tags"] = {"$all": [exact(name) for name in names]}
    return query


def now() -> datetime:
    # MongoDB keeps only milliseconds. Cut the rest, so we return the same time that we save.
    time = datetime.now(UTC)
    return time.replace(microsecond=time.microsecond // 1000 * 1000)


def not_found() -> HTTPException:
    return HTTPException(404, "Book not found")


async def save_book(db: AsyncDatabase, book: BookIn, time: datetime) -> dict:
    data = book.model_dump()
    data.update(await link_authors(db, book.author, book.author_ids))
    data["created_at"] = time
    data["updated_at"] = time
    await db.books.insert_one(data)
    data.pop("_id")
    return data


@router.get("", response_model=BookPage)
async def list_books(
    db: DB,
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    author: Annotated[str | None, Query(max_length=200)] = None,
    title: Annotated[str | None, Query(max_length=200)] = None,
    tags: Annotated[str | None, Query(max_length=500, description="Comma separated. Example: Python,Learning")] = None,
):
    query = make_filter(author, title, tags)
    total = await db.books.count_documents(query)
    skip = (page - 1) * limit
    items = await db.books.find(query, NO_ID).sort("id").skip(skip).limit(limit).to_list()
    return {"items": items, "page": page, "limit": limit, "total": total}


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: PathId, db: DB):
    book = await db.books.find_one({"id": book_id}, NO_ID)
    if book is None:
        raise not_found()
    return book


@router.post("", response_model=Book, status_code=201)
async def create_book(book: BookIn, response: Response, db: DB):
    conflict = HTTPException(409, f"A book with id {book.id} already exists")
    if await db.books.find_one({"id": book.id}):
        raise conflict
    try:
        saved = await save_book(db, book, now())
    except DuplicateKeyError:
        # Another request saved the same id at the same moment.
        raise conflict
    response.headers["Location"] = f"/books/{book.id}"
    return saved


@router.patch("/{book_id}", response_model=Book)
async def update_book(book_id: PathId, body: BookUpdate, db: DB):
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(400, "Send at least one field to change")
    if await db.books.find_one({"id": book_id}) is None:
        raise not_found()

    if "author" in changes or "author_ids" in changes:
        changes.update(await link_authors(db, changes.get("author"), changes.get("author_ids")))
    changes["updated_at"] = now()

    book = await db.books.find_one_and_update(
        {"id": book_id},
        {"$set": changes},
        projection=NO_ID,
        return_document=ReturnDocument.AFTER,
    )
    if book is None:
        raise not_found()
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: PathId, db: DB):
    result = await db.books.delete_one({"id": book_id})
    if result.deleted_count == 0:
        raise not_found()

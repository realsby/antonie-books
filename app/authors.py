from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.db import DB, IGNORE_CASE, NO_ID, next_id
from app.models import Author, AuthorIn, AuthorUpdate, AuthorWithCount, Book, PathId, split_names

router = APIRouter(prefix="/authors", tags=["authors"])


def date_text(value: date | None) -> str | None:
    # MongoDB has no "date only" type, so we save the date as text: "1960-05-30".
    return value.isoformat() if value else None


async def find_by_ids(db: AsyncDatabase, ids: list[int]) -> list[dict]:
    authors = []
    for author_id in ids:
        author = await db.authors.find_one({"id": author_id}, NO_ID)
        if author is None:
            raise HTTPException(422, f"Author {author_id} not found")
        if author not in authors:
            authors.append(author)
    return authors


async def find_by_names(db: AsyncDatabase, text: str) -> list[dict]:
    authors = []
    for name in split_names(text):
        found = await db.authors.find({"name": name}, NO_ID, collation=IGNORE_CASE).to_list()
        if len(found) > 1:
            raise HTTPException(409, f"There are {len(found)} authors called {name}. Send author_ids to choose.")

        if found:
            author = found[0]
        else:
            # A new name, so we add the author.
            # Two requests at the same moment can add the same name twice. This is rare,
            # and it is still valid data, because two authors can have the same name.
            author = {"id": await next_id(db, "authors"), "name": name, "birth_date": None}
            await db.authors.insert_one(author)
            author.pop("_id")

        if author not in authors:
            authors.append(author)
    return authors


async def link_authors(db: AsyncDatabase, author_text: str | None, author_ids: list[int] | None) -> dict:
    """Find the authors of a book by ids or by names. Return the "author" and "author_ids" fields of the book."""
    if author_ids is not None:
        authors = await find_by_ids(db, author_ids)
    else:
        authors = await find_by_names(db, author_text)
    return {
        "author": ", ".join(author["name"] for author in authors),
        "author_ids": [author["id"] for author in authors],
    }


async def find_author(db: AsyncDatabase, author_id: int) -> dict:
    author = await db.authors.find_one({"id": author_id}, NO_ID)
    if author is None:
        raise HTTPException(404, "Author not found")
    return author


@router.get("", response_model=list[AuthorWithCount])
async def list_authors(
    db: DB,
    name: Annotated[str | None, Query(max_length=200, description="Full name. Case does not matter.")] = None,
):
    query = {"name": name} if name else {}
    pipeline = [
        {"$match": query},
        {"$sort": {"id": 1}},
        # Join each author with the books that have this author id.
        {"$lookup": {"from": "books", "localField": "id", "foreignField": "author_ids", "as": "books"}},
        {"$project": {"_id": 0, "id": 1, "name": 1, "birth_date": 1, "book_count": {"$size": "$books"}}},
    ]
    cursor = await db.authors.aggregate(pipeline, collation=IGNORE_CASE)
    return await cursor.to_list()


@router.post("", response_model=Author, status_code=201)
async def create_author(body: AuthorIn, response: Response, db: DB):
    author = {"id": await next_id(db, "authors"), "name": body.name, "birth_date": date_text(body.birth_date)}
    await db.authors.insert_one(author)
    author.pop("_id")
    response.headers["Location"] = f"/authors/{author['id']}"
    return author


@router.get("/{author_id}", response_model=Author)
async def get_author(author_id: PathId, db: DB):
    return await find_author(db, author_id)


@router.get("/{author_id}/books", response_model=list[Book])
async def author_books(author_id: PathId, db: DB):
    await find_author(db, author_id)
    return await db.books.find({"author_ids": author_id}, NO_ID).sort("id").to_list()


@router.patch("/{author_id}", response_model=Author)
async def update_author(author_id: PathId, body: AuthorUpdate, db: DB):
    author = await db.authors.find_one_and_update(
        {"id": author_id},
        {"$set": {"birth_date": date_text(body.birth_date)}},
        projection=NO_ID,
        return_document=ReturnDocument.AFTER,
    )
    if author is None:
        raise HTTPException(404, "Author not found")
    return author

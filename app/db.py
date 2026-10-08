from typing import Annotated

from fastapi import Depends, Request
from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.collation import Collation

# Compare text without case. "mark lutz" is the same as "Mark Lutz".
IGNORE_CASE = Collation(locale="en", strength=2)

# Do not send the MongoDB "_id" field to the user.
NO_ID = {"_id": 0}


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db


# Use it in a route like this: async def my_route(db: DB)
DB = Annotated[AsyncDatabase, Depends(get_db)]


async def setup_db(db: AsyncDatabase):
    # create_index does nothing if the index is already there.
    await db.books.create_index("id", unique=True)
    await db.books.create_index("author_ids")
    await db.books.create_index("publisher", collation=IGNORE_CASE)
    await db.authors.create_index("id", unique=True)
    # Not unique: two authors can have the same name.
    await db.authors.create_index("name", collation=IGNORE_CASE)


async def next_id(db: AsyncDatabase, name: str) -> int:
    # One counter per collection. $inc is atomic, so two requests never get the same id.
    counter = await db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return counter["value"]


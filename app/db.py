from typing import Annotated

from fastapi import Depends, Request
from pymongo.asynchronous.database import AsyncDatabase

# Do not send the MongoDB "_id" field to the user.
NO_ID = {"_id": 0}


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db


# Use it in a route like this: async def my_route(db: DB)
DB = Annotated[AsyncDatabase, Depends(get_db)]


async def setup_db(db: AsyncDatabase):
    # create_index does nothing if the index is already there.
    await db.books.create_index("id", unique=True)

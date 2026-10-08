from datetime import datetime

from pymongo.asynchronous.database import AsyncDatabase

from app.books import save_book
from app.models import BookIn

# The sample data from the challenge.
SAMPLE_BOOKS = [
    {
        "id": 1,
        "title": "Learning Python",
        "publisher": "O'Reilly Media",
        "author": "Mark Lutz",
        "pages": 1648,
        "created_at": "2017-01-12T00:00:00+03:00",
        "tags": ["Python", "Development", "Learning"],
        "updated_at": "2017-01-12T00:00:00+03:00",
    },
    {
        "id": 2,
        "title": "Architecture Patterns with Python",
        "publisher": "O'Reilly Media",
        "author": "Harry Percival, Bob Gregory",
        "pages": 304,
        "tags": ["Python", "Development", "Functional Programming"],
        "created_at": "2017-01-12T00:00:00+03:00",
        "updated_at": "2017-01-12T00:00:00+03:00",
    },
]


async def seed(db: AsyncDatabase):
    # Add the sample books only when there are no books yet.
    if await db.books.count_documents({}) > 0:
        return
    for item in SAMPLE_BOOKS:
        time = datetime.fromisoformat(item["created_at"])
        await save_book(db, BookIn(**item), time)

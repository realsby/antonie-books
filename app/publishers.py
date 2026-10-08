from fastapi import APIRouter, HTTPException

from app.db import DB, IGNORE_CASE
from app.models import PublisherStats

router = APIRouter(prefix="/publishers", tags=["publishers"])


@router.get("/{publisher_name}/average_pages", response_model=PublisherStats)
async def average_pages(publisher_name: str, db: DB):
    pipeline = [
        {"$match": {"publisher": publisher_name}},
        {
            "$group": {
                "_id": None,
                "publisher": {"$first": "$publisher"},
                "book_count": {"$sum": 1},
                "average_pages": {"$avg": "$pages"},
            }
        },
    ]
    # The collation makes "o'reilly media" match "O'Reilly Media".
    cursor = await db.books.aggregate(pipeline, collation=IGNORE_CASE)
    result = await cursor.to_list()
    if not result:
        raise HTTPException(404, "No books found for this publisher")

    stats = result[0]
    return {
        "publisher": stats["publisher"],
        "book_count": stats["book_count"],
        "average_pages": round(stats["average_pages"], 2),
    }

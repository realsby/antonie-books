import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app import authors, books, publishers
from app.db import DB, setup_db
from app.seed import seed

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "books")

    client = AsyncMongoClient(
        mongo_url,
        tz_aware=True,  # Dates come back with their time zone (UTC).
        serverSelectionTimeoutMS=5000,
    )
    app.state.db = client[db_name]
    await setup_db(app.state.db)
    if os.getenv("SEED_DATA") == "true":
        await seed(app.state.db)

    yield
    await client.close()


app = FastAPI(title="Books API", lifespan=lifespan)
app.include_router(books.router)
app.include_router(authors.router)
app.include_router(publishers.router)


@app.get("/health", tags=["health"])
async def health(db: DB):
    await db.command("ping")
    return {"status": "ok"}

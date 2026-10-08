import os

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.seed import SAMPLE_BOOKS

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
TEST_DB = "books_test"

# Always use a separate database. The tests delete all data in it.
os.environ["DB_NAME"] = TEST_DB
os.environ["SEED_DATA"] = "false"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def mongo():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
    except Exception:
        pytest.fail(f"MongoDB is not running at {MONGO_URL}. Start it with: docker compose up -d mongo")
    yield client[TEST_DB]
    client.drop_database(TEST_DB)
    client.close()


@pytest.fixture(scope="session")
def api(mongo):
    # "with" runs the app startup, so the indexes are ready.
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_db(mongo):
    for name in ["books"]:
        mongo[name].delete_many({})


@pytest.fixture
def sample_books(api):
    for book in SAMPLE_BOOKS:
        response = api.post("/books", json=book)
        assert response.status_code == 201
    return SAMPLE_BOOKS


@pytest.fixture
def add_book(api):
    """Add a book with the API. Only send the fields you care about."""

    def add(id, **fields):
        book = {"id": id, "title": f"Book {id}", "publisher": "Test Press", "author": "Test Author", "pages": 100}
        response = api.post("/books", json={**book, **fields})
        assert response.status_code == 201, response.text
        return response.json()

    return add

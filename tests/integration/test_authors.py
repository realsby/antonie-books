def test_books_create_authors(api, sample_books):
    response = api.get("/authors")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Mark Lutz", "birth_date": None, "book_count": 1},
        {"id": 2, "name": "Harry Percival", "birth_date": None, "book_count": 1},
        {"id": 3, "name": "Bob Gregory", "birth_date": None, "book_count": 1},
    ]


def test_book_with_two_authors(api, sample_books):
    assert api.get("/books/2").json()["author_ids"] == [2, 3]


def test_same_author_any_case(api, add_book):
    add_book(1, author="Mark Lutz")
    book = add_book(2, author="mark lutz")

    assert book["author_ids"] == [1]
    authors = api.get("/authors").json()
    assert authors == [{"id": 1, "name": "Mark Lutz", "birth_date": None, "book_count": 2}]


def test_same_author_twice_in_one_book(api, add_book):
    book = add_book(1, author="Mark Lutz, Mark Lutz")
    assert book["author_ids"] == [1]


def test_book_count(api, add_book):
    add_book(1, author="Mark Lutz")
    add_book(2, author="Mark Lutz")
    add_book(3, author="Mark Lutz, Bob Gregory")

    counts = {author["name"]: author["book_count"] for author in api.get("/authors").json()}
    assert counts == {"Mark Lutz": 3, "Bob Gregory": 1}


def test_book_count_after_delete(api, sample_books):
    api.delete("/books/1")
    mark = api.get("/authors").json()[0]
    assert mark["name"] == "Mark Lutz"
    assert mark["book_count"] == 0


def test_no_authors(api):
    assert api.get("/authors").json() == []


def test_get_author(api, sample_books):
    response = api.get("/authors/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Mark Lutz", "birth_date": None}


def test_get_missing_author(api):
    assert api.get("/authors/999").status_code == 404


def test_bad_author_id(api):
    assert api.get("/authors/0").status_code == 422
    assert api.get("/authors/99999999999999999999/books").status_code == 422
    assert api.patch("/authors/abc", json={"birth_date": None}).status_code == 422


def test_author_books(api, add_book):
    add_book(1, author="Mark Lutz")
    add_book(2, author="Bob Gregory")
    add_book(3, author="Bob Gregory, Mark Lutz")

    response = api.get("/authors/1/books")
    assert response.status_code == 200
    assert [book["id"] for book in response.json()] == [1, 3]


def test_author_books_empty(api, sample_books):
    api.delete("/books/1")
    response = api.get("/authors/1/books")
    assert response.status_code == 200
    assert response.json() == []


def test_author_books_missing_author(api):
    response = api.get("/authors/999/books")
    assert response.status_code == 404
    assert response.json() == {"detail": "Author not found"}


def test_update_birth_date(api, sample_books):
    response = api.patch("/authors/1", json={"birth_date": "1960-05-30"})
    assert response.status_code == 200
    assert response.json()["birth_date"] == "1960-05-30"
    assert api.get("/authors").json()[0]["birth_date"] == "1960-05-30"


def test_clear_birth_date(api, sample_books):
    api.patch("/authors/1", json={"birth_date": "1960-05-30"})
    response = api.patch("/authors/1", json={"birth_date": None})
    assert response.json()["birth_date"] is None


def test_bad_birth_date(api, sample_books):
    assert api.patch("/authors/1", json={"birth_date": "not a date"}).status_code == 422
    assert api.patch("/authors/1", json={"birth_date": "2999-01-01"}).status_code == 422
    assert api.patch("/authors/1", json={}).status_code == 422


def test_update_missing_author(api):
    assert api.patch("/authors/999", json={"birth_date": "1960-05-30"}).status_code == 404


# --- POST /authors and books with author_ids


def test_create_author(api):
    response = api.post("/authors", json={"name": "John Smith", "birth_date": "1970-01-01"})
    assert response.status_code == 201
    assert response.headers["location"] == "/authors/1"
    assert response.json() == {"id": 1, "name": "John Smith", "birth_date": "1970-01-01"}


def test_two_authors_with_same_name(api):
    first = api.post("/authors", json={"name": "John Smith"}).json()
    second = api.post("/authors", json={"name": "John Smith", "birth_date": "1970-01-01"}).json()
    assert first["id"] != second["id"]


def test_create_bad_author(api):
    assert api.post("/authors", json={}).status_code == 422
    assert api.post("/authors", json={"name": "Smith, John"}).status_code == 422
    assert api.post("/authors", json={"name": "John Smith", "birth_date": "2999-01-01"}).status_code == 422


def test_filter_authors_by_name(api):
    api.post("/authors", json={"name": "John Smith"})
    api.post("/authors", json={"name": "John Smith"})
    api.post("/authors", json={"name": "Jane Smith"})

    response = api.get("/authors?name=john smith")
    assert [author["id"] for author in response.json()] == [1, 2]


def test_book_with_author_ids(api, add_book):
    api.post("/authors", json={"name": "Harry Percival"})
    api.post("/authors", json={"name": "Bob Gregory"})

    book = add_book(1, author=None, author_ids=[2, 1])
    # The server writes the author text from the names.
    assert book["author"] == "Bob Gregory, Harry Percival"
    assert book["author_ids"] == [2, 1]


def test_book_with_unknown_author_id(api):
    body = {"id": 1, "title": "T", "publisher": "P", "author_ids": [99], "pages": 1}
    response = api.post("/books", json=body)
    assert response.status_code == 422
    assert response.json() == {"detail": "Author 99 not found"}
    assert api.get("/books/1").status_code == 404


def test_book_needs_author_or_ids(api):
    api.post("/authors", json={"name": "Mark Lutz"})
    body = {"id": 1, "title": "T", "publisher": "P", "pages": 1}
    assert api.post("/books", json=body).status_code == 422
    assert api.post("/books", json={**body, "author": "Mark Lutz", "author_ids": [1]}).status_code == 422


def test_name_with_two_authors(api, add_book):
    api.post("/authors", json={"name": "John Smith"})
    api.post("/authors", json={"name": "John Smith"})

    body = {"id": 1, "title": "T", "publisher": "P", "author": "John Smith", "pages": 1}
    response = api.post("/books", json=body)
    assert response.status_code == 409
    assert "Send author_ids" in response.json()["detail"]

    # With the id, the client chooses the right John Smith.
    book = add_book(1, author=None, author_ids=[2])
    assert book["author"] == "John Smith"
    assert api.get("/authors/1/books").json() == []
    assert len(api.get("/authors/2/books").json()) == 1


def test_update_book_with_author_ids(api, sample_books):
    response = api.patch("/books/2", json={"author_ids": [1]})
    assert response.status_code == 200
    assert response.json()["author"] == "Mark Lutz"
    assert response.json()["author_ids"] == [1]


def test_update_book_with_unknown_author_id(api, sample_books):
    assert api.patch("/books/2", json={"author_ids": [99]}).status_code == 422
    assert api.get("/books/2").json()["author_ids"] == [2, 3]

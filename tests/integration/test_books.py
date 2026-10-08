import pytest


def ids(response):
    return [book["id"] for book in response.json()["items"]]


# --- POST /books


def test_create_book(api):
    book = {"id": 10, "title": "Fluent Python", "publisher": "O'Reilly Media", "author": "Luciano Ramalho", "pages": 1012}
    response = api.post("/books", json=book)

    assert response.status_code == 201
    assert response.headers["location"] == "/books/10"
    data = response.json()
    assert data["title"] == "Fluent Python"
    assert data["tags"] == []
    assert data["author_ids"] == [1]
    assert data["created_at"] == data["updated_at"]


def test_create_book_with_sample_json(api, sample_books):
    # The sample JSON from the challenge works as it is.
    response = api.get("/books/2")
    assert response.status_code == 200
    assert response.json()["author"] == "Harry Percival, Bob Gregory"
    # The server keeps its own times. It does not use created_at from the body.
    assert response.json()["created_at"] != sample_books[1]["created_at"]


def test_create_same_id_twice(api, add_book):
    add_book(1)
    response = api.post("/books", json={"id": 1, "title": "Other", "publisher": "P", "author": "A", "pages": 1})
    assert response.status_code == 409
    assert response.json()["detail"] == "A book with id 1 already exists"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"id": 1, "title": "No pages", "publisher": "P", "author": "A"},
        {"id": 1, "title": "Bad pages", "publisher": "P", "author": "A", "pages": "many"},
        {"id": -1, "title": "Bad id", "publisher": "P", "author": "A", "pages": 1},
        {"id": 1, "title": "No author name", "publisher": "P", "author": ",", "pages": 1},
    ],
)
def test_create_bad_book(api, body):
    response = api.post("/books", json=body)
    assert response.status_code == 422


def test_create_book_not_json(api):
    response = api.post("/books", content="hello", headers={"content-type": "application/json"})
    assert response.status_code == 422


# --- GET /books/{id}


def test_get_book(api, sample_books):
    response = api.get("/books/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Learning Python"
    assert "_id" not in response.json()


def test_get_missing_book(api):
    response = api.get("/books/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


def test_get_book_bad_id(api):
    assert api.get("/books/abc").status_code == 422


# --- GET /books


def test_list_books(api, sample_books):
    response = api.get("/books")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page"] == 1
    assert response.json()["limit"] == 10
    assert ids(response) == [1, 2]


def test_list_books_empty(api):
    response = api.get("/books")
    assert response.json() == {"items": [], "page": 1, "limit": 10, "total": 0}


def test_pagination(api, add_book):
    for id in range(1, 6):
        add_book(id)

    assert ids(api.get("/books?page=1&limit=2")) == [1, 2]
    assert ids(api.get("/books?page=2&limit=2")) == [3, 4]
    assert ids(api.get("/books?page=3&limit=2")) == [5]
    assert ids(api.get("/books?page=4&limit=2")) == []
    assert api.get("/books?page=4&limit=2").json()["total"] == 5


@pytest.mark.parametrize("params", ["page=0", "limit=0", "limit=101", "page=abc"])
def test_bad_pagination(api, params):
    assert api.get(f"/books?{params}").status_code == 422


def test_filter_by_author(api, sample_books):
    assert ids(api.get("/books?author=Mark")) == [1]
    assert ids(api.get("/books?author=bob")) == [2]
    assert ids(api.get("/books?author=Nobody")) == []


def test_filter_by_title(api, sample_books):
    assert ids(api.get("/books?title=Python")) == [1, 2]
    assert ids(api.get("/books?title=architecture")) == [2]


def test_filter_by_author_and_title(api, sample_books):
    assert ids(api.get("/books?author=Mark&title=Learning")) == [1]
    assert ids(api.get("/books?author=Mark&title=Architecture")) == []


def test_filter_by_tags(api, sample_books):
    assert ids(api.get("/books?tags=Python")) == [1, 2]
    assert ids(api.get("/books?tags=python,learning")) == [1]
    assert ids(api.get("/books?tags=Functional Programming")) == [2]
    assert ids(api.get("/books?tags=Learning,Functional Programming")) == []


def test_filter_is_not_regex(api, sample_books):
    assert ids(api.get("/books?title=.*")) == []


def test_filter_and_pagination(api, add_book):
    for id in range(1, 4):
        add_book(id, author="Mark Lutz")
    add_book(4, author="Someone Else")

    response = api.get("/books?author=Mark&limit=2&page=2")
    assert response.json()["total"] == 3
    assert ids(response) == [3]


# --- PATCH /books/{id}


def test_update_book(api, sample_books):
    before = api.get("/books/1").json()
    response = api.patch("/books/1", json={"pages": 1700, "tags": ["Python"]})

    assert response.status_code == 200
    after = response.json()
    assert after["pages"] == 1700
    assert after["tags"] == ["Python"]
    assert after["title"] == before["title"]
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] > before["updated_at"]
    assert api.get("/books/1").json() == after


def test_update_author_links_new_author(api, sample_books):
    response = api.patch("/books/1", json={"author": "mark lutz, New Writer"})
    assert response.json()["author_ids"] == [1, 4]
    assert response.json()["author"] == "Mark Lutz, New Writer"


def test_update_nothing(api, sample_books):
    response = api.patch("/books/1", json={})
    assert response.status_code == 400


def test_update_cannot_change_id(api, sample_books):
    # "id" is not a field you can change, so the body is empty.
    response = api.patch("/books/1", json={"id": 50})
    assert response.status_code == 400
    assert api.get("/books/1").status_code == 200


def test_update_bad_value(api, sample_books):
    assert api.patch("/books/1", json={"pages": 0}).status_code == 422


def test_update_missing_book(api):
    response = api.patch("/books/999", json={"pages": 10})
    assert response.status_code == 404


def test_update_missing_book_adds_no_author(api):
    api.patch("/books/999", json={"author": "Ghost Writer"})
    assert api.get("/authors").json() == []


# --- DELETE /books/{id}


def test_delete_book(api, sample_books):
    response = api.delete("/books/1")
    assert response.status_code == 204
    assert response.content == b""
    assert api.get("/books/1").status_code == 404


def test_delete_missing_book(api):
    assert api.delete("/books/999").status_code == 404


# --- Health


def test_health(api):
    assert api.get("/health").json() == {"status": "ok"}

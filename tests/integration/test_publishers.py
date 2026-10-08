def test_average_pages(api, sample_books):
    response = api.get("/publishers/O'Reilly Media/average_pages")
    assert response.status_code == 200
    # (1648 + 304) / 2 = 976
    assert response.json() == {"publisher": "O'Reilly Media", "book_count": 2, "average_pages": 976.0}


def test_average_pages_any_case(api, sample_books):
    response = api.get("/publishers/o'reilly media/average_pages")
    assert response.status_code == 200
    assert response.json()["publisher"] == "O'Reilly Media"


def test_average_pages_rounds(api, add_book):
    add_book(1, publisher="Small Press", pages=100)
    add_book(2, publisher="Small Press", pages=100)
    add_book(3, publisher="Small Press", pages=101)
    add_book(4, publisher="Other Press", pages=5000)

    response = api.get("/publishers/Small Press/average_pages")
    assert response.json() == {"publisher": "Small Press", "book_count": 3, "average_pages": 100.33}


def test_average_pages_full_name_only(api, sample_books):
    # "O'Reilly" is only a part of the name, so it does not match.
    assert api.get("/publishers/O'Reilly/average_pages").status_code == 404


def test_average_pages_unknown_publisher(api, sample_books):
    response = api.get("/publishers/Nobody/average_pages")
    assert response.status_code == 404
    assert response.json() == {"detail": "No books found for this publisher"}

# Antonie Books API

A REST API to manage books. It uses **FastAPI** and **MongoDB**.

It has:

- CRUD for books, with pagination and filters
- Authors with their own ids, and a book count for each author
- Average pages for a publisher
- Unit and integration tests
- Terraform for AWS (see [terraform/README.md](terraform/README.md))

## Project files

```
app/
  main.py         Starts the app. Connects to MongoDB. Handles database errors.
  books.py        /books endpoints
  authors.py      /authors endpoints. Links books to authors.
  publishers.py   /publishers endpoint
  models.py       Input and output models (validation)
  db.py           Indexes and the id counter
  seed.py         The sample data from the challenge
tests/
  unit/           Tests without a database
  integration/    Tests with a real MongoDB
terraform/        AWS setup
Dockerfile
docker-compose.yml
```

## Run the app

You only need Docker.

```bash
docker compose up -d --build
```

- API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

At the first start, the app adds the 2 sample books from the challenge.

Stop the app:

```bash
docker compose down        # keeps the data
docker compose down -v     # deletes the data too
```

## Database

MongoDB 8.0 runs in Docker. You do not need to set it up.

When the app starts, it creates the indexes. If `SEED_DATA=true` and there are no books, it adds the sample books.

There are 3 collections:

| Collection | What is in it |
|---|---|
| `books` | The books |
| `authors` | The authors: `id`, `name`, `birth_date` |
| `counters` | The last author id. We use it to make the next id. |

A book in the database:

```json
{
  "id": 2,
  "title": "Architecture Patterns with Python",
  "publisher": "O'Reilly Media",
  "author": "Harry Percival, Bob Gregory",
  "author_ids": [2, 3],
  "pages": 304,
  "tags": ["Python", "Development", "Functional Programming"],
  "created_at": "2017-01-11T21:00:00Z",
  "updated_at": "2017-01-11T21:00:00Z"
}
```

Settings (env variables):

| Name | Default | What it does |
|---|---|---|
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `books` | Database name |
| `MONGO_USER` | (empty) | MongoDB user. Empty locally, because local MongoDB has no login. |
| `MONGO_PASSWORD` | (empty) | MongoDB password. In AWS it comes from Secrets Manager. |
| `SEED_DATA` | (empty) | Set to `true` to add the sample books |

### How books and authors connect

Each author has its own `id`. A name is not an id: two different people can have the same name, and even the same birth date. So the book saves the author ids (`author_ids`).

When you add or change a book, you send the authors in one of 2 ways:

**1. By name** (`author`), like in the sample data: `"Harry Percival, Bob Gregory"`

1. The API splits the text by comma.
2. It looks for each author by name. Upper or lower case does not matter.
3. No author has this name: the API adds a new author.
4. One author has this name: the API uses this author.
5. More than one author has this name: the API returns `409`. It does not guess. Send `author_ids` instead.

So you can send the sample JSON as it is. You do not need to add authors first.

**2. By id** (`author_ids`), like `[2, 3]`

Use this when two authors have the same name. Find the right id with `GET /authors?name=John Smith`. Add a new author with `POST /authors`.

In both ways, the API writes the `author` text of the book from the author names. So the text and the ids always match.

If you delete a book, its authors stay. Their `book_count` goes down.

## Endpoints

| Method | Path | What it does | OK status |
|---|---|---|---|
| GET | `/books` | List books (pagination and filters) | 200 |
| GET | `/books/{id}` | Get one book | 200 |
| POST | `/books` | Add a book | 201 |
| PATCH | `/books/{id}` | Change some fields of a book | 200 |
| DELETE | `/books/{id}` | Delete a book | 204 |
| GET | `/authors` | List authors with their book count | 200 |
| POST | `/authors` | Add an author | 201 |
| GET | `/authors/{id}` | Get one author | 200 |
| GET | `/authors/{id}/books` | All books of one author | 200 |
| PATCH | `/authors/{id}` | Set the birth date of an author | 200 |
| GET | `/publishers/{name}/average_pages` | Average pages of a publisher | 200 |
| GET | `/health` | The app is running | 200 |

### GET /books

Query parameters:

| Name | Default | Rule |
|---|---|---|
| `page` | 1 | 1 to 1000000 |
| `limit` | 10 | 1 to 100 |
| `author` | | Part of the author text. Case does not matter. |
| `title` | | Part of the title. Case does not matter. |
| `tags` | | Comma separated. The book must have **all** the tags. Case does not matter. |

```bash
curl "localhost:8000/books"
curl "localhost:8000/books?page=2&limit=1"
curl "localhost:8000/books?author=Mark"
curl "localhost:8000/books?title=Python"
curl "localhost:8000/books?author=Mark&title=Learning"
curl "localhost:8000/books?tags=Python,Learning"
```

Answer:

```json
{
  "items": [
    {
      "id": 1,
      "title": "Learning Python",
      "publisher": "O'Reilly Media",
      "author": "Mark Lutz",
      "pages": 1648,
      "tags": ["Python", "Development", "Learning"],
      "author_ids": [1],
      "created_at": "2017-01-11T21:00:00Z",
      "updated_at": "2017-01-11T21:00:00Z"
    }
  ],
  "page": 1,
  "limit": 10,
  "total": 1
}
```

`total` is the number of all books that match. It is not only this page.

### GET /books/{id}

```bash
curl localhost:8000/books/1
```

It returns one book, like in the list above. If there is no book with this id, you get `404`.

### POST /books

```bash
curl -X POST localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "id": 3,
    "title": "Fluent Python",
    "publisher": "O'\''Reilly Media",
    "author": "Luciano Ramalho",
    "pages": 1012,
    "tags": ["Python", "Advanced"]
  }'
```

Answer: `201 Created`, a `Location: /books/3` header, and the new book:

```json
{
  "id": 3,
  "title": "Fluent Python",
  "publisher": "O'Reilly Media",
  "author": "Luciano Ramalho",
  "pages": 1012,
  "tags": ["Python", "Advanced"],
  "author_ids": [4],
  "created_at": "2026-10-08T20:50:36.112000Z",
  "updated_at": "2026-10-08T20:50:36.112000Z"
}
```

Rules:

- `id`, `title`, `publisher` and `pages` are required. `tags` is optional.
- Send `author` (names, comma separated) or `author_ids` (up to 20 ids), not both. See [How books and authors connect](#how-books-and-authors-connect).
- `id` is a whole number, 1 or more. It must be unique. If it is already used, you get `409`.
- `pages` is from 1 to 100000.
- Text fields are 1 to 200 characters. The API removes spaces at the start and end.
- Up to 20 tags. Each tag is 1 to 50 characters.
- The server sets `created_at` and `updated_at`. If you send them, the API ignores them.

### PATCH /books/{id}

Send only the fields you want to change. You can not change the `id`.

```bash
curl -X PATCH localhost:8000/books/3 \
  -H "Content-Type: application/json" \
  -d '{"pages": 1014}'
```

Answer: `200` and the changed book. `updated_at` has the new time.

You can change the authors with `author` or `author_ids`, like in POST.

If you send no fields, you get `400`.

### DELETE /books/{id}

```bash
curl -X DELETE localhost:8000/books/3
```

Answer: `204 No Content`, with an empty body.

### GET /authors

```bash
curl localhost:8000/authors
curl "localhost:8000/authors?name=mark%20lutz"
```

```json
[
  {"id": 1, "name": "Mark Lutz", "birth_date": null, "book_count": 1},
  {"id": 2, "name": "Harry Percival", "birth_date": null, "book_count": 1},
  {"id": 3, "name": "Bob Gregory", "birth_date": null, "book_count": 1}
]
```

`name` is optional. It is the full name, but case does not matter. It shows all authors with this name, so you can choose the right id.

### POST /authors

```bash
curl -X POST localhost:8000/authors \
  -H "Content-Type: application/json" \
  -d '{"name": "John Smith", "birth_date": "1970-01-01"}'
```

Answer: `201 Created`, a `Location: /authors/4` header, and the new author:

```json
{"id": 4, "name": "John Smith", "birth_date": "1970-01-01"}
```

- `name` is required. It can not have a comma, because books use commas between names.
- `birth_date` is optional. It can not be in the future.
- Two authors can have the same name. Each one gets its own id.

### GET /authors/{id}/books

```bash
curl localhost:8000/authors/2/books
```

It returns a list of all books of this author. If the author has no books, the list is empty. If the author does not exist, you get `404`.

### PATCH /authors/{id}

When the API adds an author from a book name, it does not know the birth date. You can set it here. You can only change `birth_date`, because books use the name.

```bash
curl -X PATCH localhost:8000/authors/1 \
  -H "Content-Type: application/json" \
  -d '{"birth_date": "1960-05-30"}'
```

This date is only an example. Send `null` to remove the date. A date in the future gives `422`.

### GET /publishers/{name}/average_pages

```bash
curl "localhost:8000/publishers/O'Reilly%20Media/average_pages"
```

```json
{"publisher": "O'Reilly Media", "book_count": 2, "average_pages": 976.0}
```

The name must be the full name, but case does not matter. If the publisher has no books, you get `404`.

## Errors

All errors have a `detail` field.

| Status | When |
|---|---|
| `400` | PATCH with no fields to change |
| `404` | The book or author does not exist |
| `409` | The book id is already used. Or an author name in a book matches more than one author. |
| `422` | Bad input: missing field, wrong type, bad page number, unknown author id, ... |
| `503` | The app can not reach MongoDB |

```json
{"detail": "Book not found"}
```

For `422`, `detail` is a list. It says which field is wrong and why:

```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "pages"], "msg": "Field required", "input": {"...": "..."}}
  ]
}
```

## Tests

There are 2 kinds of tests:

- `tests/unit`: validation and filter logic. No database.
- `tests/integration`: calls the real API with a real MongoDB.

The tests use their own database, `books_test`. They do not touch your `books` data.

**Option 1: only Docker**

```bash
docker compose run --rm tests
```

This starts MongoDB and runs all tests in a container.

**Option 2: with [uv](https://docs.astral.sh/uv/)**

```bash
docker compose up -d mongo
uv run pytest
```

Only the unit tests (no MongoDB needed):

```bash
uv run pytest tests/unit
```

## Terraform (AWS)

The `terraform/` folder has the AWS setup for production:

- ECS Fargate runs the containers in private subnets, in 2 AZs.
- An Application Load Balancer gets the HTTPS traffic.
- MongoDB Atlas is the database. The app reaches it over AWS PrivateLink, so the traffic does not go over the internet.
- The private subnets have no internet access. The containers use VPC endpoints for ECR, logs and secrets.
- The database password is not in the Terraform state.

See [terraform/README.md](terraform/README.md) for the design and the reasons.

## Decisions

- **Book id comes from the client.** The sample data has an `id`, and the task says the id is unique. A unique index protects it.
- **Author id comes from the server.** Authors can be made from book names, so the server gives the next number.
- **Names are not unique.** Two authors can have the same name. When a name is not clear, the API returns `409` and does not guess.
- **Async PyMongo.** Motor is deprecated. PyMongo now has its own async client.
- **Times are in UTC.** The sample times have `+03:00`. MongoDB saves them in UTC, so `2017-01-12T00:00:00+03:00` comes back as `2017-01-11T21:00:00Z`.
- **The sample books keep their sample times.** New books get the current time.
- **Filters are safe.** The API escapes the filter text, so a user can not send a regex. `?title=.*` looks for the text `.*`.
- **`/health` does not check the database.** The load balancer uses it. If MongoDB is down, we do not want AWS to restart all containers. API calls return `503` in that case.
- **The container runs as a normal user** (not root), with a read-only file system.

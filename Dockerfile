FROM python:3.14-slim

# uv installs the Python packages from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv

WORKDIR /code
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Install packages first. Docker can cache this step when only the code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

# Do not run as root.
RUN useradd --no-create-home --uid 1000 app
USER app

EXPOSE 8000
CMD ["/code/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

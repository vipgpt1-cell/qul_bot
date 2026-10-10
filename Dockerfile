FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies and the package first, so code-only changes reuse the cached layers above.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations

RUN useradd --system --uid 10001 --no-create-home bot
USER bot

# Apply pending migrations, then replace the shell with the bot so it receives SIGTERM.
CMD ["sh", "-c", "alembic upgrade head && exec python -m qul_bot"]

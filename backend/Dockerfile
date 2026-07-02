FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY docker-entrypoint.sh /usr/local/bin/vulnconsole-entrypoint

RUN chmod +x /usr/local/bin/vulnconsole-entrypoint \
    && useradd --create-home --uid 10001 app
USER app

ENTRYPOINT ["vulnconsole-entrypoint"]
CMD ["api"]

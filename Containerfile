from docker.io/python:3.11-bullseye as builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock LICENCE.md README.md /app/
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR


from docker.io/python:3.11-bullseye as app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHON_UNBUFFERED=1

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY influxdb_secret_controller /app/influxdb_secret_controller/
WORKDIR /app

#ENTRYPOINT ["python", "-m", "influxdb_secret_controller"]
ENTRYPOINT ["sleep", "50000"]
# Build the command service image from the monorepo root context.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the shared library first so its layer is cached across service builds.
COPY libs/python /libs/python
RUN pip install /libs/python

COPY services/command-service/pyproject.toml ./pyproject.toml
COPY services/command-service/app ./app
COPY services/command-service/migrations ./migrations
COPY services/command-service/alembic.ini ./alembic.ini
RUN pip install .

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

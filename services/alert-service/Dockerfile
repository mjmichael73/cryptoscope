# Build the alert service image from the monorepo root context.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY libs/python /libs/python
RUN pip install /libs/python

COPY services/alert-service/pyproject.toml ./pyproject.toml
COPY services/alert-service/app ./app
RUN pip install .

EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]

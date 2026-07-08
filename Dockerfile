FROM python:3.12-slim

WORKDIR /app

COPY app ./app
COPY docs ./docs
COPY events ./events
COPY issues ./issues
COPY scripts ./scripts
COPY README.md ./

ENV PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    DB_PATH=/data/devin_remediator.db

VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "-m", "app"]


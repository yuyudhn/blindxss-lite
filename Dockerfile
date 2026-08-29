# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy source
COPY app ./app
COPY wsgi.py ./wsgi.py

ENV PORT=8080 \
    DB_PATH=/data/bxss.db

# user & volume
RUN useradd -m -u 10001 appuser && mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser

EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "wsgi:app"]

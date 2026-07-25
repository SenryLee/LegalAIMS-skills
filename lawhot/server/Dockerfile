FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAWHOT_DATA_DIR=/data \
    LAWHOT_PUBLIC_BASE_URL=https://hot.fachuiai.com

WORKDIR /app

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server/app /app/app
COPY references/sources.v1.yaml /app/references/sources.v1.yaml

ENV LAWHOT_SOURCES_YAML=/app/references/sources.v1.yaml

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]

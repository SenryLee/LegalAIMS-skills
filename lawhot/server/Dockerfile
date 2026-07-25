# 默认走国内可拉的 Docker Hub 代理镜像；可用 --build-arg 覆盖
ARG BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAWHOT_DATA_DIR=/data \
    LAWHOT_PUBLIC_BASE_URL=https://hot.fachuiai.com \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server/app /app/app
COPY references/sources.v1.yaml /app/references/sources.v1.yaml

ENV LAWHOT_SOURCES_YAML=/app/references/sources.v1.yaml

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]

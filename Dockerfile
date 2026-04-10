FROM python:3.12-slim
ARG NODE_VERSION="24"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir -e .

COPY quartz /app/quartz
RUN cd quartz && npm ci

COPY vault /app/vault
COPY llmwiki.toml /app/llmwiki.toml
COPY llmwiki.toml.example /app/llmwiki.toml.example

EXPOSE 8000 8501 1313

CMD ["llmwiki", "up"]

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# System deps required by opencv and ultralytics
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first — this layer is cached until lockfile changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 5000

CMD ["uv", "run", "python", "server.py"]

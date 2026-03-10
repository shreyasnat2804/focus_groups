# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps for psycopg2-binary, numpy wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime-only deps (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app source (needed for prompts/instructions.txt and any runtime file reads)
COPY src/ src/

# Non-root user
RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8080

# gunicorn with uvicorn workers
CMD ["gunicorn", "focus_groups.api:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8080", \
     "-w", "2", \
     "--timeout", "120", \
     "--access-logfile", "-"]

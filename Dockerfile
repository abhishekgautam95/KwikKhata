# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash kwikkhata

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY ai_parser.py app.py config.py database.py main.py ./
COPY api/       api/
COPY services/  services/
COPY jobs/      jobs/
COPY models/    models/
COPY scripts/   scripts/

# Runtime directories owned by app user
RUN mkdir -p logs backups && chown -R kwikkhata:kwikkhata /app

USER kwikkhata

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

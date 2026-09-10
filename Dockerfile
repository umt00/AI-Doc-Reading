# ═══════════════════════════════════════════════════════════════
# Penta Document Intelligence — Multi-Stage Dockerfile
# ═══════════════════════════════════════════════════════════════

# ─── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.11-slim AS builder

# uv kurulumu
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Bağımlılıkları önce kopyala (Docker cache optimizasyonu)
COPY pyproject.toml requirements.txt ./

# Sanal ortam oluştur ve paketleri kur
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install -r requirements.txt

# Kaynak kodu kopyala
COPY src/ ./src/

# ─── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Güvenlik: non-root kullanıcı
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Builder'dan sanal ortamı kopyala
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# PATH'e sanal ortamı ekle
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Non-root kullanıcıya geç
USER appuser

# Port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); r.raise_for_status()" || exit 1

# Başlatma komutu
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ═══════════════════════════════════════════════════════════════════
# CP2 — Production Dockerfile (multi-stage)
#
#   Stage 1 `builder`: cài dependency vào /install (được phép nặng, bị vứt đi)
#   Stage 2 `runtime`: slim, chỉ copy thư viện đã cài + source, chạy user thường
#
# Build: docker build -t day12-agent:prod .
# ═══════════════════════════════════════════════════════════════════

# ---------- Stage 1: builder ----------
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /build

# Chỉ copy requirements trước → sửa code không làm mất cache layer pip install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# User thường, không có quyền root
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /install /usr/local

# Source code copy SAU cùng
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser utils ./utils

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=4).read()" || exit 1

# sh -c để shell thay ${PORT} — cloud tự gán cổng; exec để uvicorn là PID 1 và nhận SIGTERM
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

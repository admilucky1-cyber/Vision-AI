# Vision AI v3.2.0 — Production image
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=5050 \
    DEBUG=false

WORKDIR /app

# System deps: ffmpeg for media, curl for healthchecks, tesseract-ocr for
# scanned-PDF text extraction (pytesseract is just a Python wrapper around
# this binary), poppler-utils for pdf2image (used to rasterize PDF pages
# before OCR), graphviz for flowchart/org-chart diagram rendering (the
# graphviz pip package also just wraps this binary via `dot`).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    tesseract-ocr \
    poppler-utils \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install -U yt-dlp

COPY . .

RUN mkdir -p uploads downloads logs cache data chroma_db \
    && useradd -m -u 10001 appuser \
    && chmod +x /app/start.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5050

# Docker-native healthcheck (Railway uses HTTP /health separately)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-5050}/health" || exit 1

CMD ["python", "run.py"]

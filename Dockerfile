FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    STATS_DASHBOARD_HOST=0.0.0.0 \
    STATS_DASHBOARD_PORT=5000

WORKDIR /app

RUN addgroup -S stats && adduser -S -D -H -h /app -G stats stats

COPY requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=stats:stats app.py .
COPY --chown=stats:stats src ./src
COPY --chown=stats:stats static ./static
COPY --chown=stats:stats templates ./templates

RUN mkdir -p /app/data && chown -R stats:stats /app

USER stats

EXPOSE 5000
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=3).read()" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app:app"]

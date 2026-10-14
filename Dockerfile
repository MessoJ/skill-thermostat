FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && mkdir -p /data && chown -R appuser:appuser /data

COPY pyproject.toml README.md ./
COPY skill_thermostat ./skill_thermostat
COPY pilot ./pilot

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/')" || exit 1

CMD ["python", "-m", "pilot.study_app", "--host", "0.0.0.0", "--port", "8001", "--db", "/data/study.db"]

# ---- SkillUp container image ------------------------------------------------
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# Install dependencies first so Docker can cache this layer
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code only (tests, terraform, docs are excluded by .dockerignore)
COPY app ./app

# Run as an unprivileged user, not root
RUN useradd --system --no-create-home --uid 10001 skillup
USER 10001

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)"

# One worker keeps the in-memory demo data consistent
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--access-logfile", "-", "app.server:app"]

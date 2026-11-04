# Waste Sorting & Recycling Assistant: one image for all four subsystems.
#   docker compose up --build      ->  http://localhost:8501
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# CPU-only torch first: the default wheel brings several GB of CUDA the app never uses.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY web/requirements.txt web/requirements.txt
RUN pip install -r web/requirements.txt

# Keep the folder layout: the classifier finds models/ next to its src/ folder.
COPY classification/src    classification/src
COPY classification/models classification/models
COPY data_rules/src        data_rules/src
COPY coach/src             coach/src
COPY web/src               web/src

ENV PYTHONPATH=/app/classification/src:/app/data_rules/src:/app/coach/src:/app/web/src \
    DATABASE_URL=sqlite:////data/waste.db \
    COACH_CACHE_PATH=/data/coach_cache.db \
    DEFAULT_REGION=DO

# Scans and cached explanations live here; mount it as a volume so they survive a restart.
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser
VOLUME ["/data"]

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "web/src/web/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]

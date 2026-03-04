FROM python:3.11-slim

WORKDIR /app

# environment defaults; most platforms will override these via their UI
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENV=DEV

# production images should mount a volume at /app/faiss_data so that
# the vector index persists between restarts.  Render/Railway/AWS let you
# configure this via the dashboard.

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# install dependencies first so we can remove build tools later (reduces
# final image size)

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# remove build tools now that wheels are installed
RUN apt-get purge -y build-essential gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy backend files (app, alembic, etc.)
COPY . .

# during development a bind mount is used; in production the entire repo is
# baked into the image. you may choose to copy only `app` and `alembic` if
# you want a smaller image.

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--timeout", "120", "--bind", "0.0.0.0:8000"]
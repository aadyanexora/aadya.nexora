# Stage 1: Builder
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements to builder stage
COPY requirements.txt .

# Install CPU-only PyTorch to avoid dependency on CUDA libraries
# torch is installed as-is from PyPI (CPU variant is light)
RUN pip install --no-cache-dir \
    torch==2.0.0 \
    sentence-transformers==2.2.2

# Install all other dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime dependencies (no build-essential in final image)
RUN apt-get update && apt-get install -y \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

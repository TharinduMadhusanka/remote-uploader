FROM python:3.11-slim

WORKDIR /app

# Create non-root user matching aria2 container (UID 1000)
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser

# Install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ /app/shared/

# Copy worker code
COPY worker/ /app/worker/

# Create storage directory with proper permissions
RUN mkdir -p /app/storage/temp && \
    chown -R appuser:appuser /app

ENV PYTHONPATH=/app

# Switch to non-root user
USER appuser

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ /app/shared/

# Copy worker code
COPY worker/ /app/worker/

# Create storage directory
RUN mkdir -p /app/storage/temp

ENV PYTHONPATH=/app

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
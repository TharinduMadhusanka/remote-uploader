FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code
COPY shared/ /app/shared/

# Copy web code
COPY web/ /app/web/

# Create storage directory
RUN mkdir -p /app/storage/temp

ENV PYTHONPATH=/app

CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]
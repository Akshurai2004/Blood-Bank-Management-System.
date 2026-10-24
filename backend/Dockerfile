FROM python:3.12-slim

WORKDIR /app

# Install PostgreSQL build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn blood_bank_fastapi:app --host 0.0.0.0 --port ${PORT:-8000}"]

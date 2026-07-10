FROM python:3.13-slim

WORKDIR /workspace

# Install system dependencies needed for compiling dependencies (e.g. pg_config for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["./start.sh"]

# AIS Stream Ingestion Service
# Smart Port Intelligence System (SPIS)

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser
USER appuser

# No port exposed - this is a background service

# Run the AIS ingestion with Neo4j integration
CMD ["python", "app.py", "--mode", "live", "--neo4j"]

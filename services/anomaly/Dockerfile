# Maritime Anomaly Detection Service
# Feature 2 - Port Intelligence System

FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser
USER appuser

# Expose port 8002 (Feature 2 service)
EXPOSE 8002

# Run the FastAPI server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]

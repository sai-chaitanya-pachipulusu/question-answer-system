# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model (optional, for NER)
# Commented out to reduce image size - can enable if needed
# RUN python -m spacy download en_core_web_sm

# Copy application code
COPY app.py .
COPY qa_engine.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (Railway provides dynamic PORT)
EXPOSE 8080

# Run with gunicorn for production
# Use shell form to allow $PORT variable expansion
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 2 --timeout 120 --log-level info app:app


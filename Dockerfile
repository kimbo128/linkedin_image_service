FROM python:3.12-slim

# Install system dependencies including fonts
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p templates generated

# Expose port
EXPOSE $PORT

# Run the application
CMD gunicorn app:app --bind 0.0.0.0:$PORT


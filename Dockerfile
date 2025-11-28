FROM python:3.12-slim

# Install system dependencies including fonts
RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    fonts-dejavu \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p templates generated

# Make start script executable
RUN chmod +x start.sh

# Expose port (default 5000)
EXPOSE 5000

# Run the application
CMD ["bash", "start.sh"]


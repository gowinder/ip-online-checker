FROM python:3.9-alpine

WORKDIR /app

# Install system dependencies needed for ping and arp
RUN apk add --no-cache \
    iputils \
    net-tools

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the monitoring script
COPY monitor.py .

# Create directories for logs
RUN mkdir -p /app/logs

# Make the script executable
RUN chmod +x monitor.py

# Default command
CMD ["python", "monitor.py", "/config/config.yaml"]
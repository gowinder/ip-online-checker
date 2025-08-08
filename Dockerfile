FROM python:3.9-alpine

WORKDIR /app

# Install system dependencies needed for ping and arp
RUN apk add --no-cache \
    iputils \
    net-tools

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the monitoring scripts and version file
COPY monitor.py multi_monitor.py version.py .

# Create directories for logs
RUN mkdir -p /app/logs

# Make the scripts executable
RUN chmod +x monitor.py multi_monitor.py

# Default command
CMD ["python", "multi_monitor.py", "/config/config.yaml"]
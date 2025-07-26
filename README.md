# Network Monitor

A simple tool to monitor network connectivity to a specific IP or MAC address and log online/offline events with duration tracking.

## Features

- Monitor connectivity to a target IP or MAC address
- Log online/offline events with timestamps and durations
- Slack notifications for state changes
- Docker containerization for easy deployment
- Configurable ping intervals and offline thresholds

## Setup

1. Modify `config.yaml` to set your target IP/MAC address and other settings
2. If using Slack notifications, update the webhook URL and enable notifications
3. Run with Docker: `docker-compose up -d`

## Configuration

The `config.yaml` file contains the following settings:

- `target.ip`: IP address to monitor (used if MAC is empty)
- `target.mac`: MAC address to monitor (takes precedence over IP if provided)
- `ping_interval`: Seconds between ping attempts
- `offline_threshold`: Seconds before declaring device offline
- `log_file`: Path to the log file
- `slack.enabled`: Enable/disable Slack notifications
- `slack.webhook_url`: Slack webhook URL for notifications
- `slack.channel`: Slack channel to send notifications to

## Log Format

Logs are written in the format:
```
20250713_221000->20250713_222000 [在线10分钟]
20250713_222000->20250713_222500 [离线5分钟]
```

## Running

### With Docker (Recommended)

```bash
docker-compose up -d
```

### Direct Python Execution

```bash
pip install -r requirements.txt
python monitor.py
```

## Notes

- When using MAC address monitoring, the tool checks the ARP table
- The tool requires appropriate network permissions for ping and ARP commands
- In Docker, `network_mode: host` is used to allow proper network access
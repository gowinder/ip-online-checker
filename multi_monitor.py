#!/usr/bin/env python3

import datetime
import os
import subprocess
import sys
import threading
import time

import requests
import yaml

from version import VERSION


class NetworkMonitor:
    def __init__(self, target_config: dict, global_config: dict, log_path: str):
        """Initialize the network monitor with target configuration."""
        self.target_ip = target_config['ip']
        self.target_mac = target_config.get('mac', '')
        self.enable = target_config.get('enable', True)
        self.ping_interval = target_config.get('ping_interval', global_config.get('global_ping_interval', 5))
        self.offline_threshold = target_config.get('offline_threshold', global_config.get('global_offline_threshold', 60))
        self.online_threshold = target_config.get('online_threshold', 60)  # Default 1 minute
        self.heartbeat_interval = global_config.get('global_heartbeat_interval', 300)  # Default 5 minutes
        
        # Generate log file path based on IP address
        safe_ip = self.target_ip.replace('.', '_')
        self.log_file = os.path.join(log_path, f"mon_{safe_ip}.log")
        
        # Slack configuration
        slack_config = global_config.get('slack', {})
        self.slack_enabled = slack_config.get('enabled', False)
        self.slack_webhook_url = slack_config.get('webhook_url', '')
        self.slack_channel = slack_config.get('channel', '')
        
        # State tracking
        self.is_online = False
        self.last_state_change = None
        self.offline_start_time = None
        self.online_start_time = None
        self.start_time = datetime.datetime.now()
        self.last_heartbeat_time = datetime.datetime.now()
        
        # Use MAC if provided, otherwise use IP
        self.target = self.target_mac if self.target_mac else self.target_ip
        self.use_mac = bool(self.target_mac)
        
    def ping_target(self) -> bool:
        """Ping the target IP or check ARP table for MAC address."""
        try:
            if self.use_mac:
                # Check ARP table for MAC address
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
                return self.target.lower() in result.stdout.lower()
            else:
                # Ping the IP address
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', str(self.ping_interval), self.target],
                    capture_output=True
                )
                return result.returncode == 0
        except Exception as e:
            print(f"Error pinging target: {e}")
            sys.stdout.flush()
            return False
    
    def log_event(self, message: str, log_to_file: bool = True):
        """Log an event to the console and optionally to a file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Print to console with flush
        print(log_entry.strip())
        sys.stdout.flush()
        
        # Write to log file if enabled
        if log_to_file:
            try:
                os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
                with open(self.log_file, 'a') as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"Error writing to log file: {e}")
                sys.stdout.flush()
    
    def send_slack_notification(self, message: str):
        """Send a notification to Slack if enabled."""
        if not self.slack_enabled or not self.slack_webhook_url:
            return
            
        try:
            payload = {
                "text": message,
                "channel": self.slack_channel
            }
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"Failed to send Slack notification: {response.status_code}")
                sys.stdout.flush()
        except Exception as e:
            print(f"Error sending Slack notification: {e}")
            sys.stdout.flush()
    
    def format_duration(self, start_time: datetime.datetime, end_time: datetime.datetime) -> str:
        """Format the duration between two timestamps."""
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def send_heartbeat(self):
        """Send a heartbeat log to show the program is still running."""
        current_time = datetime.datetime.now()
        if current_time - self.last_heartbeat_time >= datetime.timedelta(seconds=self.heartbeat_interval):
            # Calculate current state duration
            if self.last_state_change:
                state_duration_str = self.format_duration(self.last_state_change, current_time)
            else:
                state_duration_str = "0秒"
            
            # Calculate total running time
            running_time_str = self.format_duration(self.start_time, current_time)
            
            # Send heartbeat log
            state_str = "在线" if self.is_online else "离线"
            heartbeat_msg = f"[心跳] 当前状态: {state_str} | 持续时间: {state_duration_str} | 运行时间: {running_time_str}"
            self.log_event(heartbeat_msg, log_to_file=False)
            
            # Update last heartbeat time
            self.last_heartbeat_time = current_time
    
    def record_state_change(self, new_state: bool):
        """Record a state change (online/offline) with timestamp."""
        current_time = datetime.datetime.now()
        
        if self.last_state_change is not None:
            # Record the previous state duration
            duration_str = self.format_duration(self.last_state_change, current_time)
            if self.is_online:
                # Was online, now going offline
                start_str = self.last_state_change.strftime("%Y%m%d_%H%M%S")
                end_str = current_time.strftime("%Y%m%d_%H%M%S")
                log_message = f"{start_str}->{end_str} [在线{duration_str}]"
                self.log_event(log_message)
                
                # Send Slack notification for offline event
                notification_msg = f"设备 {self.target} 已下线，持续时间: {duration_str}"
                self.send_slack_notification(notification_msg)
            else:
                # Was offline, now going online
                start_str = self.last_state_change.strftime("%Y%m%d_%H%M%S")
                end_str = current_time.strftime("%Y%m%d_%H%M%S")
                log_message = f"{start_str}->{end_str} [离线{duration_str}]"
                self.log_event(log_message)
                
                # Send Slack notification for online event
                notification_msg = f"设备 {self.target} 已上线，离线持续时间: {duration_str}"
                self.send_slack_notification(notification_msg)
        
        # Update state tracking
        self.is_online = new_state
        self.last_state_change = current_time
        self.offline_start_time = None if new_state else current_time
        self.online_start_time = current_time if new_state else None
    
    def run(self):
        """Main monitoring loop."""
        if not self.enable:
            self.log_event(f"目标 {self.target} 未启用，跳过监控")
            return
            
        self.log_event(f"开始监控目标: {self.target} ({'MAC' if self.use_mac else 'IP'})")
        
        # Initialize state
        initial_state = self.ping_target()
        self.is_online = initial_state
        self.last_state_change = datetime.datetime.now()
        
        if initial_state:
            self.log_event("初始状态: 在线")
        else:
            self.log_event("初始状态: 离线")
            
        while True:
            try:
                current_state = self.ping_target()
                
                # Handle state transitions with threshold for offline state
                if current_state != self.is_online:
                    if current_state:  # Going online
                        # Start tracking online time but don't immediately declare online
                        if self.online_start_time is None:
                            self.online_start_time = datetime.datetime.now()
                        else:
                            # Check if we've been online long enough
                            online_duration = datetime.datetime.now() - self.online_start_time
                            if online_duration.total_seconds() >= self.online_threshold:
                                self.record_state_change(True)
                                self.log_event("状态变更: 在线")
                                self.online_start_time = None
                    else:  # Going offline
                        # Start tracking offline time but don't immediately declare offline
                        if self.offline_start_time is None:
                            self.offline_start_time = datetime.datetime.now()
                        else:
                            # Check if we've been offline long enough
                            offline_duration = datetime.datetime.now() - self.offline_start_time
                            if offline_duration.total_seconds() >= self.offline_threshold:
                                self.record_state_change(False)
                                self.log_event("状态变更: 离线")
                                self.offline_start_time = None
                else:
                    # Reset tracking if we're back in the same state
                    if current_state:
                        self.online_start_time = None
                    else:
                        self.offline_start_time = None
                
                # Send heartbeat if needed
                self.send_heartbeat()
                
                time.sleep(self.ping_interval)
                
            except KeyboardInterrupt:
                self.log_event("监控已停止")
                # Record final state before exiting
                if self.last_state_change is not None:
                    final_time = datetime.datetime.now()
                    duration_str = self.format_duration(self.last_state_change, final_time)
                    state_str = "在线" if self.is_online else "离线"
                    start_str = self.last_state_change.strftime("%Y%m%d_%H%M%S")
                    end_str = final_time.strftime("%Y%m%d_%H%M%S")
                    log_message = f"{start_str}->{end_str} [{state_str}{duration_str}]"
                    self.log_event(log_message)
                break
            except Exception as e:
                self.log_event(f"监控错误: {e}")
                time.sleep(self.ping_interval)


class MultiNetworkMonitor:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the multi-network monitor with configuration file."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.targets = self.config.get('targets', [])
        self.global_config = {k: v for k, v in self.config.items() if k != 'targets'}
        self.log_path = self.config.get('log_path', './logs')
        
        # Create monitor instances for each target
        self.monitors = []
        for target_config in self.targets:
            monitor = NetworkMonitor(target_config, self.global_config, self.log_path)
            self.monitors.append(monitor)
    
    def run(self):
        """Run all monitors in separate threads."""
        print("version: ", VERSION)
        if not self.monitors:
            print("没有配置监控目标")
            return
        
        threads = []
        for monitor in self.monitors:
            if monitor.enable:
                thread = threading.Thread(target=monitor.run)
                thread.daemon = True
                thread.start()
                threads.append(thread)
        
        # Wait for all threads to complete (they won't in normal operation)
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            print("多目标监控已停止")


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config_multi.yaml"
    monitor = MultiNetworkMonitor(config_path)
    monitor.run()
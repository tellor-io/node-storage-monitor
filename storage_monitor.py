#!/usr/bin/env python3
"""
Storage Monitor for Debian/Linux
Monitors specific directories and system storage, sends Discord alerts via webhook.
"""

import os
import json
import shutil
import subprocess
import urllib.request
import time
from pathlib import Path
from typing import Dict, Tuple, Optional


class StorageMonitor:
    def __init__(self, webhook_url: str, state_file: str = "storage_monitor_state.json", 
                 send_status_reports: bool = False, server_name: str = "Server"):
        self.webhook_url = webhook_url
        self.state_file = state_file
        self.send_status_reports = send_status_reports
        self.server_name = server_name
        self.home_dir = Path.home()
        
        # Thresholds (in GB for directories, % for system storage)
        self.thresholds = {
            'layer_dir': {'warning': 10.0, 'critical': 20.0},  # GB
            'home_dir': {'warning': 50.0, 'critical': 100.0},  # GB
            'journal_logs': {'warning': 5.0, 'critical': 10.0},  # GB
            'system_storage': {'warning': 80.0, 'critical': 95.0}  # %
        }
        
        self.last_states = self.load_state()
    
    def load_state(self) -> Dict[str, str]:
        """Load last alert states from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def save_state(self):
        """Save current alert states to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.last_states, f, indent=2)
        except Exception as e:
            print(f"Failed to save state: {e}")
    
    def get_directory_size(self, path: Path) -> float:
        """Get directory size in GB."""
        if not path.exists():
            return 0.0
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, PermissionError):
            return 0.0
        
        return total_size / (1024**3)  # Convert to GB
    
    def get_home_dir_size_excluding_layer(self) -> float:
        """Get home directory size excluding ~/.layer in GB."""
        layer_dir = self.home_dir / ".layer"
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.home_dir):
                # Skip .layer directory
                if layer_dir.exists() and dirpath.startswith(str(layer_dir)):
                    continue
                
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, PermissionError):
            return 0.0
        
        return total_size / (1024**3)  # Convert to GB
    
    def get_journal_size(self) -> float:
        """Get systemd journal logs size in GB."""
        try:
            result = subprocess.run(
                ['journalctl', '--disk-usage'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse output like "Archived and active journals take up 1.2G in the file system."
                output = result.stdout.strip()
                if "take up" in output:
                    size_part = output.split("take up")[1].split("in the file system")[0].strip()
                    
                    # Extract number and unit
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*([KMGT]?)B?', size_part)
                    if match:
                        size_value = float(match.group(1))
                        unit = match.group(2).upper()
                        
                        # Convert to GB
                        multipliers = {'': 1/(1024**3), 'K': 1/(1024**2), 'M': 1/1024, 'G': 1, 'T': 1024}
                        return size_value * multipliers.get(unit, 1/(1024**3))
        except Exception:
            pass
        
        return 0.0
    
    def get_system_storage(self) -> Tuple[float, float, float]:
        """Get system storage usage percentage, free GB, total GB."""
        try:
            total, used, free = shutil.disk_usage('/')
            usage_percent = (used / total) * 100
            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            return usage_percent, free_gb, total_gb
        except Exception:
            return 0.0, 0.0, 0.0
    
    def determine_alert_level(self, value: float, thresholds: Dict[str, float], is_percentage: bool = False) -> str:
        """Determine alert level based on value and thresholds."""
        if value >= thresholds['critical']:
            return 'critical'
        elif value >= thresholds['warning']:
            return 'warning'
        else:
            return 'normal'
    
    def send_discord_alert(self, message: str):
        """Send alert to Discord webhook."""
        try:
            data = {"content": message}
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(data).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'StorageMonitor/1.0'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 204:
                    print("Alert sent successfully")
                else:
                    print(f"Alert sent with status: {response.status}")
        except Exception as e:
            print(f"Failed to send Discord alert: {e}")
    
    def format_alert_message(self, metric_name: str, value: float, unit: str, level: str, 
                           threshold_warning: float, threshold_critical: float) -> str:
        """Format alert message for Discord."""
        emoji_map = {'warning': '⚠️', 'critical': '🚨', 'normal': '✅'}
        emoji = emoji_map.get(level, '📊')
        
        message = f"{emoji} **{self.server_name} - {metric_name}** - {level.upper()}\n"
        message += f"Current: {value:.2f} {unit}\n"
        message += f"Warning: {threshold_warning:.2f} {unit}\n"
        message += f"Critical: {threshold_critical:.2f} {unit}"
        
        return message
    
    def format_status_report(self, layer_size: float, home_size: float, journal_size: float, 
                           sys_usage: float, sys_free: float, sys_total: float) -> str:
        """Format a comprehensive status report for Discord."""
        message = f"**🪖 Storage Status for {self.server_name}**\n"
        message += f"**Home Directory (excl .layer):** {home_size:.2f} GB\n"
        message += f"**~/.layer Directory:** {layer_size:.2f} GB\n"
        message += f"**Journal Logs:** {journal_size:.2f} GB\n"
        message += f"**System Storage:** {sys_usage:.1f}% used ({sys_free:.1f} GB free of {sys_total:.1f} GB total)\n\n"

        return message
    
    def check_and_alert(self):
        """Main monitoring function."""
        print("Starting storage check...")
        
        # Check ~/.layer directory
        layer_size = self.get_directory_size(self.home_dir / ".layer")
        layer_level = self.determine_alert_level(layer_size, self.thresholds['layer_dir'])
        
        # Check home directory (excluding ~/.layer)
        home_size = self.get_home_dir_size_excluding_layer()
        home_level = self.determine_alert_level(home_size, self.thresholds['home_dir'])
        
        # Check journal logs
        journal_size = self.get_journal_size()
        journal_level = self.determine_alert_level(journal_size, self.thresholds['journal_logs'])
        
        # Check system storage
        sys_usage, sys_free, sys_total = self.get_system_storage()
        sys_level = self.determine_alert_level(sys_usage, self.thresholds['system_storage'], True)
        
        # Print current status
        print(f"~/.layer: {layer_size:.2f} GB ({layer_level})")
        print(f"~/ (excl .layer): {home_size:.2f} GB ({home_level})")
        print(f"Journal logs: {journal_size:.2f} GB ({journal_level})")
        print(f"System storage: {sys_usage:.1f}% used, {sys_free:.1f} GB free ({sys_level})")
        
        # Check for alerts
        alerts_to_send = []
        
        metrics = [
            ('layer_dir', '~/.layer Directory', layer_size, layer_level, 'GB'),
            ('home_dir', 'Home Directory (excl .layer)', home_size, home_level, 'GB'),
            ('journal_logs', 'Journal Logs', journal_size, journal_level, 'GB'),
            ('system_storage', 'System Storage', sys_usage, sys_level, '%')
        ]
        
        for metric_key, metric_name, value, current_level, unit in metrics:
            last_level = self.last_states.get(metric_key, 'normal')
            
            # Send alert if level changed and not normal, or if recovering from critical/warning
            should_alert = False
            
            if current_level != 'normal' and last_level != current_level:
                should_alert = True
            elif current_level == 'normal' and last_level != 'normal':
                should_alert = True  # Recovery alert
            
            if should_alert:
                thresholds = self.thresholds[metric_key]
                message = self.format_alert_message(
                    metric_name, value, unit, current_level,
                    thresholds['warning'], thresholds['critical']
                )
                alerts_to_send.append(message)
            
            # Update state
            self.last_states[metric_key] = current_level
        
        # Send alerts
        if alerts_to_send:
            full_message = "\n\n".join(alerts_to_send)
            self.send_discord_alert(full_message)
        else:
            print("No alerts to send")
        
        # Send status report if enabled
        if self.send_status_reports:
            status_message = self.format_status_report(
                layer_size, home_size, journal_size, 
                sys_usage, sys_free, sys_total
            )
            self.send_discord_alert(status_message)
            print("Status report sent")
        
        # Save state
        self.save_state()
        print("Storage check completed")


def main():
    
    # Try to load configuration from config.py, fallback to hardcoded values
    try:
        import config
        WEBHOOK_URL = config.WEBHOOK_URL
        custom_thresholds = getattr(config, 'CUSTOM_THRESHOLDS', None)
        state_file = getattr(config, 'STATE_FILE', "storage_monitor_state.json")
        check_interval = getattr(config, 'CHECK_INTERVAL_HOURS', 24)
        send_status_reports = getattr(config, 'SEND_STATUS_REPORTS', False)
        server_name = getattr(config, 'SERVER_NAME', 'Server')
    except ImportError:
        # Fallback configuration
        WEBHOOK_URL = "https://discord.com/api/webhooks/1394315684002922568/7WnbZRSVTvtNzlpvqSPVjg7j-FZ1yNnNB1AuMd7CTsEFNO80GXE6Qd8eVEJ980RjiDyU"  # Replace with your Discord webhook URL
        custom_thresholds = None
        state_file = "storage_monitor_state.json"
        check_interval = 24  # Default to 24 hours
        send_status_reports = False  # Default to disabled
        server_name = 'Server'  # Default server name
    
    if WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print("Please set your Discord webhook URL!")
        print("Either:")
        print("1. Edit the WEBHOOK_URL variable in storage_monitor.py")
        print("2. Create config.py based on config_example.py")
        return
    
    monitor = StorageMonitor(WEBHOOK_URL, state_file, send_status_reports, server_name)
    
    # Apply custom thresholds if provided
    if custom_thresholds:
        monitor.thresholds.update(custom_thresholds)
    
    print(f"Storage Monitor started for '{server_name}'. Checking every {check_interval} hours.")
    print(f"Status reports: {'Enabled' if send_status_reports else 'Disabled'}")
    print("Press Ctrl+C to stop.")
    
    # Run the monitoring loop
    while True:
        try:
            monitor.check_and_alert()
            
            # Wait for the specified interval (in seconds)
            sleep_time = check_interval * 3600  # Convert hours to seconds
            time.sleep(sleep_time)
                    
        except Exception as e:
            print(f"Error during monitoring: {e}")
            # Wait 5 minutes before retrying on error
            time.sleep(300)


if __name__ == "__main__":
    main() 
"""
Configuration example for storage_monitor.py

Copy this to config.py and customize the values for your setup.
"""

# Your Discord webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# Custom thresholds (optional - script has sensible defaults)
CUSTOM_THRESHOLDS = {
    'layer_dir': {'warning': 350.0, 'critical': 390.0},      # GB
    'home_dir': {'warning': 10.0, 'critical': 25.0},      # GB
    'journal_logs': {'warning': 5.0, 'critical': 10.0},    # GB
    'system_storage': {'warning': 75.0, 'critical': 80.0}  # %
}

# State file location (optional)
STATE_FILE = "storage_monitor_state.json"

# Check interval in hours (optional - defaults to 24 hours)
CHECK_INTERVAL_HOURS = 24

# Send status reports every time the script runs (optional - defaults to False)
# When enabled, sends a summary of all storage metrics even when no thresholds are breached
SEND_STATUS_REPORTS = False

# Server name to include in alerts and status reports (optional - defaults to "Server")
SERVER_NAME = "My Server"

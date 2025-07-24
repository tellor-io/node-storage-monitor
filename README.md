# node-storage-monitor
Simple discord alerts for when your tellor node server's storage is getting full.

## Prerequisites:
- uv https://docs.astral.sh/uv/getting-started/installation/
- A discord webhook

## Installation and Operation:
1. Clone the repo:
```
git clone https://github.com/tellor-io/node-storage-monitor
```
2. Make a python environment for running the monitor. We will use uv because it's in style:
```
cd node-storage-monitor && uv venv && source .venv/bin/activate
```
3. Copy config_example.py to config.py and edit with your unique configuration:
```
cp config_example.py config.py && nano config.py
```
4. Run this command in tmux or screen:
```
python storage_monitor.py
```

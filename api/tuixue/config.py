import os
import json
from datetime import datetime
from threading import Lock

lock = Lock()

def load_config():
    global config
    with lock:
        with open("config.json", "r") as f:
            config = json.load(f)
        return datetime.now()

def save_config():
    global config
    with lock:
        with open("config.json", "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

config = {}
last_update = load_config()

def get(item):
    global config, last_update
    current_time = datetime.now()
    if (current_time - last_update).total_seconds() > 180:
        last_update = load_config()
    return config.get(item)

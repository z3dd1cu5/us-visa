import os
import json
from threading import Lock

lock = Lock()

def load_config():
    global config
    with lock:
        with open("config.json", "r") as f:
            config = json.load(f)

def save_config():
    global config
    with lock:
        with open("config.json", "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

config = {}
load_config()

def get(*args):
    global config
    with lock:
        tmp = config
        for arg in args:
            tmp = tmp.get(arg, {})
        return tmp

def set(value, *args):
    global config
    with lock:
        if len(args) == 1:
            config[args[0]] = value
        elif len(args) == 2:
            config[args[0]][args[1]] = value
        elif len(args) == 3:
            config[args[0]][args[1]][args[2]] = value

def delete(*args):
    global config
    with lock:
        if len(args) == 1:
            del config[args[0]]
        elif len(args) == 2:
            del config[args[0]][args[1]]
        elif len(args) == 3:
            del config[args[0]][args[1]][args[2]]

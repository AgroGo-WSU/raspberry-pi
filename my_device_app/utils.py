"""
utils.py
- Shared utility functions:
  - get_mac(): returns MAC address as string XX:XX:...
  - load_local_config(), save_local_config() for persistent config storage
  - HTTP helper wrappers (simple)
  - basic logging helper that writes to stdout and app.log
"""

import os
import json
import uuid
import tempfile
import time
from typing import Dict, Any

CONFIG_PATH = "/home/pi/my_device_app/config.json"
LOG_PATH = "/home/pi/my_device_app/logs/app.log"


def get_mac() -> str:
    """
    Return MAC address in canonical colon-separated format.
    Uses uuid.getnode() fallback; on Linux this should be stable.
    """
    mac_int = uuid.getnode()
    mac_str = ":".join([f"{(mac_int >> ele) & 0xff:02x}" for ele in range(0, 8 * 6, 8)][::-1])
    return mac_str.lower()


def load_local_config() -> Dict[str, Any]:
    """
    Load config.json if it exists, otherwise create a default skeleton.
    Returns a dict that always contains at least deviceId, paired(boolean).
    """
    default = {
        "deviceId": None,
        "paired": False,
        "firebaseUid": None,
        "pairing_nonce": None,
        "last_config_fetch": None,
        "backend": {
            "config_url_template": "https://dev.agrogo.org/device/{mac}/config",
            "upload_url_template": "https://dev.agrogo.org/device/{mac}/data"
        },
        "pinActionTable": [],
        "last_seen": {}
    }

    # create directory if needed
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    if not os.path.exists(CONFIG_PATH):
        save_local_config(default)
        return default

    try:
        with open(CONFIG_PATH, "r") as fh:
            cfg = json.load(fh)
    except Exception:
        # If file corrupted, overwrite a default
        save_local_config(default)
        return default

    # Ensure default keys exist
    for k, v in default.items():
        if k not in cfg:
            cfg[k] = v
    return cfg


def save_local_config(data: Dict[str, Any]) -> None:
    """
    Atomically write config.json to prevent corruption on power loss.
    """
    # Use atomic write via tempfile then replace
    dirpath = os.path.dirname(CONFIG_PATH)
    fd, tmpfile = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmpfile, CONFIG_PATH)
    finally:
        if os.path.exists(tmpfile):
            try:
                os.remove(tmpfile)
            except Exception:
                pass


def log_info(msg: str) -> None:
    """
    Simple logger that prints to stdout and appends to LOG_PATH.
    Systemd can capture stdout; we still append to a file for convenience.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"{timestamp} - {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a") as fh:
            fh.write(line + "\n")
    except Exception:
        # if logging fails (permissions, missing dir) ignore silently
        pass


# Short helper wrappers for HTTP to keep main code readable
import requests


def http_get_json(url: str, headers: dict = None, params: dict = None, timeout: int = 10):
    """
    GET request that returns parsed JSON or raises.
    """
    r = requests.get(url, headers=headers or {}, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def http_post_json(url: str, body: dict, headers: dict = None, timeout: int = 10):
    """
    POST JSON; returns response object.
    """
    r = requests.post(url, json=body, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r
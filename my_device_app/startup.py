"""
startup.py
- Entry script run at boot (systemd).
- Loads local config. If not paired -> runs pairing.py.
  If paired -> runs main.py.
- Keeps things simple: uses subprocess.run to execute child scripts
  so logs appear in stdout/stderr (captured by systemd -> logs/app.log).
"""

import os
import subprocess
import sys
from utils import load_local_config, is_paired, get_mac

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PAIRING_SCRIPT = os.path.join(APP_DIR, "pairing.py")
MAIN_SCRIPT = os.path.join(APP_DIR, "main.py")


def main():
    # Ensure config exists and has deviceId set (MAC-based)
    config = load_local_config()  # this will create config.json if missing
    # Ensure the config has deviceId populated with MAC address
    if not config.get("deviceId"):
        mac = get_mac()
        if mac:
            config["deviceId"] = mac
            # save deviceId back to persistent config
            from utils import save_local_config
            save_local_config(config)

    if not is_paired(config):
        print("[startup] Device not paired. Launching pairing script.")
        # Run pairing (blocking). pairing.py will save pairing info when done.
        subprocess.run([sys.executable, PAIRING_SCRIPT])
    else:
        print("[startup] Device paired. Launching main application.")
        subprocess.run([sys.executable, MAIN_SCRIPT])


if __name__ == "__main__":
    main()
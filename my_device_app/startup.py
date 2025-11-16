"""
startup.py
- Entry script run at boot (systemd).
- Loads local config. If not paired -> runs pairing.py.
  If paired -> runs main.py.
- Keeps things simple: uses subprocess.run to execute child scripts
  so logs appear in stdout/stderr (captured by systemd -> logs/app.log).
"""
import os
import sys
import subprocess
import time
import pytz
from utils import load_local_config, save_local_config, get_mac, log_info

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PAIRING_SCRIPT = os.path.join(APP_DIR, "pairing.py")
MAIN_SCRIPT = os.path.join(APP_DIR, "main.py")


def main():
    log_info("[startup] Starting device startup process...")
    
    #Ensure config exists and load it
    config = load_local_config()

    #Ensure MAC address is saved in config as 'mac'
    mac = config.get("mac")
    if not mac:
        mac = get_mac()
        if mac:
            config["mac"] = mac
            save_local_config(config)
            log_info(f"[startup] Saved device MAC address: {mac}")
        else:
            log_info("[startup] ERROR: Could not determine MAC address.")
            return

    #Check pairing state
    paired = config.get("paired", False)
    if not paired:
        log_info("[startup] Device not paired. Starting pairing process...")
        result = subprocess.run([sys.executable, PAIRING_SCRIPT])

        if result.returncode != 0:
            log_info("[startup] Pairing script exited with an error.")
            return

        # Reload config after pairing attempt
        config = load_local_config()
        paired = config.get("paired", False)

    #If paired, launch main.py
    if paired:
        log_info("[startup] Device is paired. Launching main.py...")
        time.sleep(2)  # optional short delay
        subprocess.run([sys.executable, MAIN_SCRIPT])
    else:
        log_info("[startup] Pairing not completed. Exiting.")


if __name__ == "__main__":
    main()
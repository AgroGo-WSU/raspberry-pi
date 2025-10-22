"""
pairing.py
- Displays a terminal QR containing a pairing URL with the Pi's MAC + nonce.
- Polls backend pairing-check endpoint until backend reports mapping (firebaseUid)
  for this MAC. Once pairing confirmed, writes firebaseUid to local config.json.
- Backend endpoints expected:
  - GET "URL"
    returns { "firebaseUid": "firebase|UUID..." } when paired, else {} / 404 / 204.
"""

import os
import time
import uuid
import secrets
import qrcode
import requests
from utils import get_mac, load_local_config, save_local_config, log_info

# Backend pairing status endpoint
PAIRING_STATUS_URL = "https://backend.agrogodev.workers.dev/api/raspi/pairingStatus"

# Poll interval (seconds)
POLL_INTERVAL = 8


def generate_nonce():
    return secrets.token_urlsafe(16)


def build_pairing_url(mac: str) -> str:
    # Pairing web app will accept mac and nonce and present Firebase login UI.
    return f"https://agrogo-wsu.github.io/device-pairing?mac={mac}" #&nonce={nonce}"


def show_qr_terminal(url: str) -> None:
    # Use qrcode to create ASCII QR
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    # Print ASCII QR (inverting makes it easier to scan on dark terminal backgrounds)
    qr.print_ascii(invert=True)


def wait_for_pairing(mac: str):
    """
    Polls backend for pairing status. Server should verify nonce and return firebaseUid.
    Response example: { "firebaseUid": "firebase|abc123", "message": "paired" }
    """
    log_info(f"[pairing] Polling pairing status for MAC={mac}")
    url = PAIRING_STATUS_URL
    while True:
        try:
            resp = requests.get(url, params={"mac": mac,}, timeout=10)
            if resp.status_code == 200:
                j = resp.json()
                firebase_uid = j.get("firebaseUid") or j.get("firebase_uid")
                if firebase_uid:
                    log_info(f"[pairing] Pairing confirmed by backend. firebaseUid={firebase_uid}")
                    return firebase_uid
            else:
                # server might return 204 / 404 if not found — continue polling
                log_info(f"[pairing] pairing check status: {resp.status_code}")
        except Exception as e:
            log_info(f"[pairing] Error contacting server: {e}")
        time.sleep(POLL_INTERVAL)


def main():
    mac = get_mac()
    if not mac:
        print("[pairing] ERROR: Could not determine MAC address.")
        return

    config = load_local_config()

    # Create a nonce and persist to config to allow server-side verification if needed
    """once = config.get("pairing_nonce")
    if not nonce:
        nonce = generate_nonce()
        config["pairing_nonce"] = nonce
        save_local_config(config)"""

    pairing_url = build_pairing_url(mac)
    print("[pairing] Scan this QR code with your phone to sign in and pair the device:")
    show_qr_terminal(pairing_url)
    print(f"[pairing] Pairing URL (also visible as text): {pairing_url}")

    # Wait until backend reports pairing
    firebase_uid = wait_for_pairing(mac)

    # Save pairing info locally
    config["firebaseUid"] = firebase_uid
    config["paired"] = True
    save_local_config(config)
    print("[pairing] Pairing complete. Saved config locally.")

    # Optionally, exit so startup or user can run main.py next (or startup can exec main)
    # We'll exit here; startup.py calls pairing.py when needed.
    return


if __name__ == "__main__":
    main()

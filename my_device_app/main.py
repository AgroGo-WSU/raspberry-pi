"""
main.py
- Main runtime for the Pi device.
- Responsibilities:
  - Determine deviceId (MAC).
  - Fetch config JSON from backend (URL template from utils.load_local_config()).
  - Read DHT11 sensor on GPIO 15 periodically.
  - Execute scheduled actions from pinActionTable.
  - Evaluate sensor-based triggers in the pinActionTable as well if present.
  - Upload telemetry to backend.
  - Persist last known config to local config.json.

Notes:
- pinActionTable entry format expected (unified table):
  {
    "type": "fan" | "water",
    "pin": 17,
    "time": "HH:MM",           # optional: scheduled daily activation time (24h)
    "duration": 300,           # seconds
    // optional sensor triggers:
    "trigger": "temp_above" | "temp_below" | "humidity_above" | "humidity_below",
    "value": 75.0
  }
- Scheduling behavior:
  - If "time" present, action runs when local HH:MM matches current time (checked every loop)
  - Prevent repeated triggers within the same minute using in-memory 'recent_runs'
- Requirements:
  - Adafruit_DHT (pip package 'Adafruit_DHT' or system package)
  - RPi.GPIO
  - requests
"""
import time
import threading
import datetime
import traceback

import RPi.GPIO as GPIO
import adafruit_dht
import board
import numpy as np
import pytz

from utils import (
    get_mac,
    load_local_config,
    save_local_config,
    http_get_json,
    http_post_json,
    log_info,
)

# ---------- Hardware pin definitions (BCM numbering) ----------
DHT_PIN = board.D15  # DHT11 data line on GPIO 15
dht_device = adafruit_dht.DHT11(DHT_PIN, use_pulseio=False)

PIN_MAP = {
    "fan": 17,
    "water_1": 27,
    "water_2": 22,
    "water_3": 23
}
CONTROL_PINS = list(PIN_MAP.values())

recent_runs = {}
gpio_lock = threading.Lock()

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for p in CONTROL_PINS:
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)

# ---------- Timezone setup ----------
LOCAL_TZ = pytz.timezone("America/Detroit")

ALERT_URL = "https://backend.agrogodev.workers.dev/raspi/alert"

# ---------- Helper functions ----------
def activate_pin(pin: int, duration: float):
    """Activate GPIO pin HIGH for 'duration' seconds, then LOW."""
    def _worker():
        try:
            with gpio_lock:
                log_info(f"[GPIO] Activating pin {pin} HIGH for {duration}s")
                GPIO.output(pin, GPIO.HIGH)
            time.sleep(duration)
        except Exception as e:
            log_info(f"[GPIO] Error in activation worker: {e}")
        finally:
            with gpio_lock:
                try:
                    GPIO.output(pin, GPIO.LOW)
                    log_info(f"[GPIO] Pin {pin} set LOW after {duration}s")
                except Exception as e:
                    log_info(f"[GPIO] Error setting pin LOW: {e}")
    threading.Thread(target=_worker, daemon=True).start()


def should_run_scheduled_action(entry, now):
    """Return True if entry should run this minute based on its time field."""
    when = entry.get("time")
    if not when:
        return False
    try:
        hh_mm = when.strip()
        now_str = now.strftime("%H:%M")
        if hh_mm != now_str:
            return False
        entry_key = f"scheduled:{entry.get('type')}:{entry.get('pin')}:{when}"
        last = recent_runs.get(entry_key)
        if last and int(last // 60) == int(now.timestamp() // 60):
            return False
        recent_runs[entry_key] = now.timestamp()
        return True
    except Exception as e:
        log_info(f"[sched] Error parsing scheduled time '{when}': {e}")
        return False


def should_run_sensor_trigger(entry, readings):
    """Evaluate sensor-based triggers like temp_above, humidity_below, etc."""
    trig = entry.get("trigger")
    value = entry.get("value")
    if not trig or value is None:
        return False

    temp = readings.get("temperature")
    humidity = readings.get("humidity")

    condition = False
    if trig == "temp_above" and temp is not None:
        condition = temp > value
    elif trig == "temp_below" and temp is not None:
        condition = temp < value
    elif trig == "humidity_above" and humidity is not None:
        condition = humidity > value
    elif trig == "humidity_below" and humidity is not None:
        condition = humidity < value
    if not condition:
        return False

    entry_key = f"sensor:{entry.get('type')}:{entry.get('pin')}:{trig}:{value}"
    now_ts = time.time()
    cooldown = entry.get("cooldown", max(60, entry.get("duration", 60)))
    last = recent_runs.get(entry_key)
    if last and (now_ts - last) < cooldown:
        return False
    recent_runs[entry_key] = now_ts
    return True


def read_dht11():
    """Read DHT11 sensor safely and return dict of readings."""
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        if temperature_c is None or humidity is None:
            log_info("[sensor] DHT11 returned None values.")
            return {}
        log_info(f"[sensor] DHT11 reading: Temp={temperature_c:.1f}°C  Humidity={humidity:.1f}%")
        return {"temperature": temperature_c, "humidity": humidity}
    except RuntimeError as e:
        log_info(f"[sensor] RuntimeError during read: {e}")
        time.sleep(2)
        return {}
    except Exception as e:
        log_info(f"[sensor] Unexpected exception: {e}")
        try:
            dht_device.exit()
        except Exception:
            pass
        time.sleep(2)
        return {}
def fetch_remote_config(config_url: str) -> dict:
    log_info(f"[main] Fetching config from {config_url}")
    return http_get_json(config_url, timeout=10)

def compare_pin_tables(old_table, new_table) -> bool:
    try:
        log_info(f"[compare] Old pinActionTable: {old_table}")
        log_info(f"[compare] New pinActionTable: {new_table}")
        old_arr = np.array(old_table, dtype=object)
        new_arr = np.array(new_table, dtype=object)
        if old_arr.shape != new_arr.shape:
            return True
        return not np.array_equal(old_arr, new_arr)
    except Exception as e:
        log_info(f"[compare] Error comparing pin tables: {e}")
        return True

def notify_backend_change(firebase_uid: str):
    payload = {
        "userId": firebase_uid,
        "message": "Device config updated successfully.",
        "severity": "blue",
    }
    try:
        http_post_json(ALERT_URL, payload)
        log_info("[notify] Sent config update message.")
    except Exception as e:
        log_info(f"[notify] Failed to send update: {e}")

# ---------- Main ----------
def main():
    log_info("[main] Starting main runtime")
    cfg = load_local_config()

    mac = cfg.get("mac") or get_mac()
    cfg["mac"] = mac

    backend_cfg = cfg.get("backend", {})
    config_url_template = backend_cfg.get(
        "config_url_template",
        "https://backend.agrogodev.workers.dev/raspi/{mac}/pinActionTable"
    )
    upload_url_template = backend_cfg.get(
        "upload_url_template",
        "https://backend.agrogodev.workers.dev/raspi/{mac}/sensorReadings"
    )

    def fetch_and_store_config():
        try:
            config_url = config_url_template.format(mac=mac)
            remote_cfg = fetch_remote_config(config_url)
            old_pin_table = cfg.get("pinActionTable", [])
            new_pin_table = remote_cfg.get("data", [])
            changed = compare_pin_tables(old_pin_table, new_pin_table)

            if changed:
                log_info("[main] Detected changes in pinActionTable. Updating local config.")
                cfg["pinActionTable"] = new_pin_table
                cfg["last_config_fetch"] = time.time()
                save_local_config(cfg)
                firebase_uid = cfg.get("firebaseUUID") or cfg.get("firebaseUid")
                if firebase_uid:
                    notify_backend_change(firebase_uid)
                else:
                    log_info("[main] No Firebase UID found, skipping notification.")
            else:
                log_info("[main] No change detected in pinActionTable.")
                return True
        except Exception as e:
            log_info(f"[main] Error fetching config: {e}")
        return False
   
    # Initial fetch
    fetch_and_store_config()

    sampling_interval = int(cfg.get("samplingInterval", 30))
    config_refetch_interval = int(cfg.get("configRefetchInterval", 30))
    last_config_refetch = time.time()

    try:
        while True:
            loop_start = time.time()
            now = datetime.datetime.now(datetime.timezone.utc).astimezone(LOCAL_TZ)

            if (time.time() - last_config_refetch) > config_refetch_interval:
                log_info("[main] Checking for backend config updates...")
                if fetch_and_store_config():
                    cfg = load_local_config()
                last_config_refetch = time.time()
              
            pin_table = cfg.get("pinActionTable", [])
            readings = read_dht11()
            if readings:
                log_info(f"[main] Sensor readings: {readings}")
            else:
                log_info("[main] No sensor readings this loop.")
            for entry in pin_table:
                    try:
                        if should_run_scheduled_action(entry, now):
                            pin = int(entry.get("pin"))
                            duration = int(entry.get("duration", 30))
                            activate_pin(pin, duration)
                            log_info(f"[sched] Scheduled action triggered for pin {pin} duration={duration}")

                        if readings and should_run_sensor_trigger(entry, readings):
                            pin = int(entry.get("pin"))
                            duration = int(entry.get("duration", 30))
                            activate_pin(pin, duration)
                            log_info(f"[sensor-trigger] Triggered pin {pin} due to sensor rule: {entry.get('trigger')}")
                    except Exception as e:
                        log_info(f"[main] Error evaluating entry {entry}: {e}")
                        log_info(traceback.format_exc())
                
                # Upload telemetry
            upload_url = upload_url_template.format(mac=mac)
            try:
                if readings:
                    upload_url = upload_url_template.format(mac=mac)
                    payload = {"reading": str(readings)}
                    http_post_json(upload_url, payload, timeout=10)
                    log_info(f"[upload] Telemetry uploaded to {upload_url}")
            except Exception as e:
                log_info(f"[upload] Failed to upload telemetry: {e}")
                            
            elapsed = time.time() - loop_start
            sleep_for = max(1, sampling_interval - int(elapsed))
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        log_info("[main] KeyboardInterrupt received, cleaning up GPIO and exiting.")
    except Exception as e:
        log_info(f"[main] Unhandled exception: {e}")
        log_info(traceback.format_exc())
    finally:
        GPIO.cleanup()
        log_info("[main] Shutdown complete.")

if __name__ == "__main__":
    main()

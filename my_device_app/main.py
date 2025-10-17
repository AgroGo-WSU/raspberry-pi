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
import Adafruit_DHT

from utils import (
    get_mac,
    load_local_config,
    save_local_config,
    http_get_json,
    http_post_json,
    log_info,
)

# ---------- Hardware pin definitions (BCM numbering) ----------
DHT_PIN = 15  # DHT11 data line on GPIO 15 (as requested)
DHT_SENSOR = Adafruit_DHT.DHT11

PIN_MAP = {
    "fan": 17,
    "water_1": 27,
    "water_2": 22,
    "water_3": 23
}
# For quick lookup: set of all controlled pins
CONTROL_PINS = list(PIN_MAP.values())

# -------------- Runtime state --------------
# Used to ensure we don't retrigger scheduled actions multiple times in the same minute
recent_runs = {}  # key -> last_run_timestamp (epoch sec)

# Thread-safe lock for GPIO activation to avoid concurrent writes from multiple triggers
gpio_lock = threading.Lock()

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for p in CONTROL_PINS:
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)


# ---------- Helper functions ----------
def activate_pin(pin: int, duration: float):
    """
    Activate a GPIO pin (HIGH) for 'duration' seconds, then set LOW.
    Uses a separate thread so main loop is not blocked by long durations.
    Multiple activations of the same pin will be serialized by gpio_lock.
    """
    def _worker():
        try:
            with gpio_lock:
                log_info(f"[GPIO] Activating pin {pin} HIGH for {duration}s")
                GPIO.output(pin, GPIO.HIGH)
            # Sleep outside lock so multiple pins can run concurrently
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

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def should_run_scheduled_action(entry: dict, now: datetime.datetime) -> bool:
    """
    Determine if an entry with 'time' should run now.
    We match by exact minute. Prevent retriggering if already run within same minute.
    """
    when = entry.get("time")
    if not when:
        return False
    try:
        # Accept "HH:MM" format
        hh_mm = when.strip()
        now_str = now.strftime("%H:%M")
        if hh_mm != now_str:
            return False
        # Build a unique key for last-run tracking
        entry_key = f"scheduled:{entry.get('type')}:{entry.get('pin')}:{when}"
        last = recent_runs.get(entry_key)
        # Only run if not run in the current minute
        if last and int(last // 60) == int(now.timestamp() // 60):
            return False
        # Otherwise allow run
        recent_runs[entry_key] = now.timestamp()
        return True
    except Exception as e:
        log_info(f"[sched] Error parsing scheduled time '{when}': {e}")
        return False


def should_run_sensor_trigger(entry: dict, readings: dict) -> bool:
    """
    Evaluate sensor-based triggers like temp_above, humidity_below, etc.
    Returns True if trigger condition satisfied and not recently triggered.
    """
    trig = entry.get("trigger")
    if not trig:
        return False
    value = entry.get("value")
    if value is None:
        return False

    # Read values from readings dict
    temp = readings.get("temp")
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

    # Rate-limit repeated triggers for this entry (use key based on type+pin+trigger)
    entry_key = f"sensor:{entry.get('type')}:{entry.get('pin')}:{trig}:{value}"
    last = recent_runs.get(entry_key)
    now_ts = time.time()
    # If last run within 'cooldown' seconds -> skip. Use duration or default 60s
    cooldown = entry.get("cooldown", max(60, entry.get("duration", 60)))
    if last and (now_ts - last) < cooldown:
        return False
    recent_runs[entry_key] = now_ts
    return True


def read_dht11() -> dict:
    """
    Read DHT11 sensor via Adafruit_DHT.read_retry().
    Returns dict: {"temp": float, "humidity": float} or {} on failure.
    """
    try:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        if humidity is None or temperature is None:
            log_info("[sensor] DHT11 read returned None (sensor might be disconnected).")
            return {}
        # DHT11 returns integer-ish values; convert to float for precision later
        return {"temp": float(temperature), "humidity": float(humidity)}
    except Exception as e:
        log_info(f"[sensor] Exception reading DHT11: {e}")
        return {}


# ---------- Main runtime ----------
def main():
    log_info("[main] Starting main runtime")
    cfg = load_local_config()

    # Ensure deviceId set to MAC
    device_id = cfg.get("deviceId") or get_mac()
    cfg["deviceId"] = device_id

    # Backend endpoints from config (templates)
    backend_cfg = cfg.get("backend", {})
    config_url_template = backend_cfg.get(
        "config_url_template", "https://dev.agrogo.com/device/{mac}/config"
    )
    upload_url_template = backend_cfg.get(
        "upload_url_template", "https://dev.agrogo.com/device/{mac}/data"
    )
    ## honestly I dont know if this will work but if we can its no biggie we can do
    ## something more manual
    # Basic headers: if firebaseUid present you can later exchange for ID token
    headers = {}
    if cfg.get("firebaseUid"):
        # For now we include firebaseUid as Authorization placeholder; swap for real token if available
        headers["Authorization"] = f"Bearer {cfg.get('firebaseUid')}"

    # Fetch config (and re-fetch periodically)
    def fetch_and_store_config():
        try:
            config_url = config_url_template.format(mac=device_id)
            log_info(f"[main] Fetching config from {config_url}")
            j = http_get_json(config_url, headers=headers, timeout=10)
            # Merge into local config and persist
            cfg.update(j)
            cfg["last_config_fetch"] = time.time()
            save_local_config(cfg)
            log_info("[main] Config fetched and saved locally.")
            return True
        except Exception as e:
            log_info(f"[main] Error fetching config: {e}")
            return False

    # Initial fetch
    fetch_and_store_config()

    # Polling and action loop
    sampling_interval = int(cfg.get("samplingInterval", 900))
    config_refetch_interval = int(cfg.get("configRefetchInterval", 600))  # seconds

    last_config_refetch = time.time()

    try:
        while True:
            loop_start = time.time()
            now = datetime.datetime.now()

            # Re-fetch config periodically
            if (time.time() - last_config_refetch) > config_refetch_interval:
                fetch_and_store_config()
                last_config_refetch = time.time()
                # reload pinActionTable from persisted cfg
                pin_table = cfg.get("pinActionTable", [])
            else:
                pin_table = cfg.get("pinActionTable", [])

            # Read sensor values
            readings = read_dht11()
            if readings:
                log_info(f"[main] Sensor readings: {readings}")
            else:
                log_info("[main] No sensor readings this loop.")

            # Evaluate scheduled actions (time-based)
            for entry in pin_table:
                try:
                    # Scheduled actions
                    if should_run_scheduled_action(entry, now):
                        pin = int(entry.get("pin"))
                        duration = int(entry.get("duration", 60))
                        activate_pin(pin, duration)
                        log_info(f"[sched] Scheduled action triggered for pin {pin} duration={duration}")

                    # Sensor-based triggers
                    if readings and should_run_sensor_trigger(entry, readings):
                        pin = int(entry.get("pin"))
                        duration = int(entry.get("duration", 60))
                        activate_pin(pin, duration)
                        log_info(f"[sensor-trigger] Triggered pin {pin} due to sensor rule: {entry.get('trigger')}")

                except Exception as e:
                    log_info(f"[main] Error evaluating entry {entry}: {e}")
                    log_info(traceback.format_exc())

            # Upload telemetry if uploadUrl present
            upload_url = cfg.get("uploadUrl") or upload_url_template.format(mac=device_id)
            if readings and upload_url:
                payload = {
                    "deviceId": device_id,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "readings": readings,
                }
                try:
                    http_post_json(upload_url, payload, headers=headers, timeout=10)
                    log_info(f"[upload] Telemetry uploaded to {upload_url}")
                except Exception as e:
                    log_info(f"[upload] Failed to upload telemetry: {e}")

            # Sleep until next sampling interval (account for loop time)
            elapsed = time.time() - loop_start
            sleep_for = max(1, sampling_interval - int(elapsed))
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        log_info("[main] KeyboardInterrupt received, cleaning up GPIO and exiting.")
    except Exception as e:
        log_info(f"[main] Unhandled exception: {e}")
        log_info(traceback.format_exc())
    finally:
        try:
            GPIO.cleanup()
        except Exception:
            pass
        log_info("[main] Shutdown complete.")


if __name__ == "__main__":
    main()
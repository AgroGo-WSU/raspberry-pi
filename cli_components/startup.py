from cloud.worker_client import send_sensor
from sensors import dummy  # TODO: replace with actual data
from pathlib import Path
import json

PERSIST_PATH = "./persistent_data_store/sensors.txt"
DEFAULT_USER_ID = "73d2c45f-c17b-4d92-9938-34ccf301b78b"

def display_startup(logged_in, stdscr, start_line=0):
    """Displays the startup menu and registers any new sensors."""
    if not logged_in:
        stdscr.addstr(start_line, 0, "User not logged in, sign in by scanning the QR code below")
        return

    stdscr.addstr(start_line, 0, "User logged in, initializing sensor readings")
    reading = dummy.read_all()

    # Loop through readings dynamically
    for i, (sensor_type, value) in enumerate(reading.items(), start=1):
        sensor = {"userId": DEFAULT_USER_ID, "type": sensor_type, "zone": f"{sensor_type}_zone"}
        payload = {k: sensor[k] for k in ("userId", "type", "zone")}

        result = save_sensors([sensor], PERSIST_PATH, payload)
        line_offset = start_line + i + 1
        if "0 new sensors saved" not in result:
            resp = send_sensor(DEFAULT_USER_ID, sensor_type, sensor["zone"])
            stdscr.addstr(line_offset, 0, f"Registered {sensor_type} sensor: {resp}")
        else:
            stdscr.addstr(line_offset, 0, f"{sensor_type.capitalize()} sensor already exists locally")
        stdscr.refresh()


def save_sensors(sensors, file_path, payload):
    """Save sensor data locally and avoid duplicates."""
    file = Path(file_path)
    file.parent.mkdir(parents=True, exist_ok=True)
    if not file.exists():
        file.touch()

    existing_sensors = {}
    try:
        with open(file, "r") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("uuid"):
                        existing_sensors[rec["uuid"]] = rec
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return f"Error reading file: {e}"

    new_records = []
    for sensor in sensors:
        uuid = sensor.get("uuid")
        if uuid and uuid in existing_sensors:
            continue
        new_records.append({**payload, "uuid": uuid})

    if not new_records:
        return "0 new sensors saved"

    try:
        with open(file, "a") as f:
            for rec in new_records:
                f.write(json.dumps(rec) + "\n")
    except Exception as e:
        return f"Error writing to file: {e}"

    return f"{len(new_records)} new sensors saved"

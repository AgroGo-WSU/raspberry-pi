import time
from datetime import datetime
from sensors.read_sensors import read_sensors
from cloud.worker_client import send_sensor_reading_to_d1

SENSOR_STORAGE_PATH = "./persistent_data_store/sensors.txt"
DEFAULT_USER_ID = "73d2c45f-c17b-4d92-9938-34ccf301b78b"
SEND_INTERVAL_SECONDS = 15 # 15 minutes

def display_dashboard():
    """Continuously read sensors and send readings to D1 every 15 minutes."""
    sensor_uuids = find_sensor_uuids_in_storage(SENSOR_STORAGE_PATH)
    
    if not sensor_uuids:
        print("No sensors found in storage. Please register sensors first")
        return
    
    while True:
        sensor_data = read_sensors()
        print(f"\n=== Current Sensor Readings ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")

        for sensor in sensor_data:
            name = sensor.get("name")
            value = sensor.get("reading")
            uuid = sensor_uuids.get(name)

            if not uuid:
                print(f"{name}: UUID not found in storage")
                continue

            print(f"{name}: {value} (sending to D1)")
            try:
                response = send_sensor_reading_to_d1(reading=value, user_id=DEFAULT_USER_ID, sensor_id=uuid)
                print(f"Sent reading for '{name}' successfully --> {response}")
            except Exception as e:
                print(f"Failed to send reading for {name}: {e}")

        
        print(f"Sleeping for {SEND_INTERVAL_SECONDS / 60:.0f} minutes...\n")
        time.sleep(SEND_INTERVAL_SECONDS)
    

def find_sensor_uuids_in_storage(file_path):
    """
    Reads the sensor storage file and returns a dict mapping
    sensor names to their UUIDs.
    
    Example output:
    {
        "temp_1": "0f170d06-884d-4dfe-82e0-9c365c10ab4c",
        "hum_1": "1e0cbe3b-a8dd-4798-af50-80dd93a28371"
    }
    """
    sensor_uuids = {}

    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue

                # Expecting format: <sensor name>, uuid: <uuid>
                if ", uuid: " in line:
                    name, uuid = line.split(", uuid: ")
                    sensor_uuids[name] = uuid
                else:
                    # Fallback if line is malformed
                    print(f"Skipping malformed line: {line}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    
    return sensor_uuids
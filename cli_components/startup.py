import json
from cloud.worker_client import send_sensor_to_d1
from sensors import dummy  # TODO: replace with actual data
from pathlib import Path

#PERSIST_PATH = "./persistent_data_store/sensors.txt"
PERSIST_PATH = Path(__file__).resolve().parent / "persistent_data_store" / "sensors.txt"
DEFAULT_USER_ID = "73d2c45f-c17b-4d92-9938-34ccf301b78b"
DEFAULT_ZONE_ID = "cfecaee9-69e9-4f57-b3c5-0a57831a6731"

def display_startup(logged_in):
    """Displays the startup menu and registers any new sensors."""
    if not logged_in:
        print("User not logged in, sign in by scanning the QR code below")
        return "startup"

    print("User logged in, initializing sensor readings")

    save_new_sensors_to_storage(
        DEFAULT_ZONE_ID, 
        DEFAULT_USER_ID, 
        dummy.read_all(), 
        PERSIST_PATH
    )

    # Direct the user the dashboard screen
    return "dashboard"

# Nick, Madeline, you may need to edit the 2 methods below. They work
# with my specific formatting of the dummy data
def save_new_sensors_to_storage(zone, user_id, sensor_list, file_path):
    """
    Checks if each sensor in sensor_dict exists in the file.
    If not, it appends the new sensor name to the file.
    """

    for sensor in sensor_list:
        sensor_name = sensor["name"]
        sensor_type = sensor["type"]

        sensor_exists_in_file = is_sensor_in_file(sensor_name, file_path)
        if sensor_exists_in_file: continue

        # Save the new sensor log both in D1 and locally
        try:
            response = send_sensor_to_d1(user_id, sensor_type, zone)

            # Separate the JSON from response string
            if isinstance(response, str):
                response = json.loads(response)
            
            # Throw an error if the response failed
            if not response.get("success"):
                raise Exception(f"Server responded with status {response}")

            # Save the record to the storage in the format:
            # <name>, uuid: <sensor uuid>
            sensor_uuid = response["data"]["sensorId"]
            with open(file_path, "a") as f:
                f.write(f"{sensor_name}, uuid: {sensor_uuid}\n")
            print(f"Sensor '{sensor_name}' registered successfully.")
        except Exception as e:
            print(f"Failed to register '{sensor_name}': {e}")


def is_sensor_in_file(sensor, file_path):
    """
    Checks whether the given sensor name exists in the file.
    Returns True if found, False otherwise.
    """

    try:
        with open(file_path, "r") as f:
            for line in f:
                if line.strip() == sensor: return True
            return False
    except FileNotFoundError:
        # File doesn't exist yet, so the sensor can't be in it
        return False
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return False
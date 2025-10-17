import requests
import json
from datetime import datetime
from pathlib import Path

def send_temperature_reading_to_d1(reading, user_id, sensor_id):
    """Makes a new temperature entry in the pings table in D1"""

    base_url = "https://backend.agrogodev.workers.dev/api/data/pings"
    headers = make_headers()

    payload = {
        "userId": user_id,
        # TODO add physical reading once it's been added into the database
        "sensorId": sensor_id,
        "time": datetime.now()
    }

    post_record(base_url, headers, json.dumps(payload))

def send_humidity_reading_to_d1(reading, user_id, sensor_id):
    """Makes a new humidity entry in the pings table in D1"""

    base_url = "https://backend.agrogodev.workers.dev/api/data/pings"
    headers = make_headers()

    payload = {
        "userId": user_id,
        # TODO add physical reading once it's been added into the database
        "sensorId": sensor_id,
        "time": datetime.now()
    }

    post_record(base_url, headers, json.dumps(payload))

def send_sensor_to_d1(user_id, type, zone):
    """Makes a new entry in the sensor table in D1"""

    base_url = "https://backend.agrogodev.workers.dev/api/data/sensors"
    headers = make_headers()

    payload = {
        "userId": user_id,
        "type": type,
        "zone": zone
    }
    
    # Send data to backend
    response = post_record(base_url, headers, json.dumps(payload))
    print(response)
    return response

# File that holds the bearer token. Add the bearer token and only the bearer token
# in the file '../persistent_data_store/beared_token.txt'
TOKEN_PATH = Path(__file__).resolve().parent.parent / "persistent_data_store" / "bearer_token.txt"
def get_bearer_token():
    """Read the bearer token from file, return empty string if not found."""
    try:
        with open(TOKEN_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Bearer token file not found. Please log in first")
        return ""
    except Exception as e:
        print(f"Error reading bearer token: {e}")

def make_headers():
    """Returns the Content-Type and Authorization headers needed for all Cloudflare D1 API calls"""
    bearer_token = get_bearer_token()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

def post_record(base_url, headers, data):
    """Try/catch block that includes error checking for a D1 POST request"""
    try:
        response = requests.post(base_url, headers=headers, data=data)

        if response.status_code == 200:
            return "Data send successfully: " + json.dumps(response.json())
        else:
            return f"Failed to send data ({response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return "Error sending data: " + e
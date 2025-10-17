import requests
import json
from datetime import datetime

# DO NOT COMMIT
bearer_token = ""

def send_temperature_reading(reading, user_id, sensor_id):
    base_url = "https://backend.agrogodev.workers.dev/api/data/pings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    payload = {
        "userId": user_id,
        # TODO add physical reading once it's been added into the database
        "sensorId": sensor_id,
        "time": datetime.now()
    }

    post_record(base_url, headers, json.dumps(payload))

def send_humidity_reading(reading, user_id, sensor_id):
    base_url = "https://backend.agrogodev.workers.dev/api/data/pings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    payload = {
        "userId": user_id,
        # TODO add physical reading once it's been added into the database
        "sensorId": sensor_id,
        "time": datetime.now()
    }

    post_record(base_url, headers, json.dumps(payload))

def send_sensor(user_id, type, zone):
    base_url = "https://backend.agrogodev.workers.dev/api/data/sensors"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}"
    }

    payload = {
        "userId": user_id,
        # TODO add physical reading once it's been added into the database
        "type": type,
        "zone": zone
    }
    
    # Send data to backend
    response = post_record(base_url, headers, json.dumps(payload))
    return response

def post_record(base_url, headers, data):
    try:
        response = requests.post(base_url, headers=headers, data=data)

        if response.status_code == 200:
            return "Data send successfully: " + json.dumps(response.json())
        else:
            return f"Failed to send data ({response.status_code}): {response.text}"
    except requests.exceptions.RequestException as e:
        return "Error sending data: " + e
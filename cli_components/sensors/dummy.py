import random

# Nick, Madeline, this is our current source of sensor readings, 
# Remove this file and change any references to this file to 
# wherever you end up having the sensor readings sourced from.
# This file is referenced in startup.py, read_sensors.py
def read_all():
    """Return a dict of dummy sensor readings"""
    return [
        {
            "name": "temp_1",
            "reading": round(60 + random.uniform(-10, 10)),
            "type": "temperature"
        },
        {
            "name": "hum_1",
            "reading": round(40 + random.uniform(-5, 5)),
            "type": "humidity"
        }
    ]
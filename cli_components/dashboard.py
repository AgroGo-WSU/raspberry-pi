from sensors.read_sensors import read_sensors

def display_dashboard():
    sensor_data = read_sensors()

    print("=== Current Sensor Readings ===")

    for sensor in sensor_data:
        print(f"{sensor}: {sensor_data[sensor]}")
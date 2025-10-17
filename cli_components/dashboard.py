from sensors.read_sensors import read_sensors

def display_dashboard(stdscr, start_line):
    sensor_data = read_sensors()

    stdscr.addstr(start_line, 0, "=== Current Sensor Readings ===")
    
    i = start_line + 1
    for sensor in sensor_data:
        stdscr.addstr(i, 0, f"{sensor}: {sensor_data[sensor]}")
        i += 1
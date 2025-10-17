from .dummy import read_all

def read_sensors():
    """Returns live sensor readings (dummy for now)"""
    # TODO: This is dummy data, point this to actual sensors
    return read_all()
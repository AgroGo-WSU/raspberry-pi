import random

def read_all():
    """Return a dict of dummy sensor readings"""
    return {
        "temperature_f": round(60 + random.uniform(-10, 10)),
        "humidity_pct": round(40 + random.uniform(-5, 5))
    }
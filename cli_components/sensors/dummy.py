import random

def read_all():
    """Return a dict of dummy sensor readings"""
    return {
        "temperature": round(60 + random.uniform(-10, 10)),
        "humidity": round(40 + random.uniform(-5, 5))
    }
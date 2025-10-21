import RPi.GPIO as GPIO
import time

PIN_MAP = {
    "fan": 17,
    "water_1": 27,
    "water_2": 22,
    "water_3": 23
}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for p in CONTROL_PINS:
    GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)

print("GPIO pin Test Started — Press Ctrl+C to stop\n")

try:
    while True:
        for name, pin in PIN_MAP.items():
            print(f"Activating {name} on GPIO {pin}")
            GPIO.output(pin, GPIO.HIGH)
            time.sleep(5)  # ON duration
            GPIO.output(pin, GPIO.LOW)
            print(f"{name} OFF\n")
            time.sleep(2)  # OFF delay

except KeyboardInterrupt:
    print("\nTest stopped by user.")

finally:
    GPIO.cleanup()
    print("GPIO cleaned up. All pins set to LOW.")


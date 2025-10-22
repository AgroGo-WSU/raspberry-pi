import time
import adafruit_dht
import board

# DHT11 on GPIO15 (pin 10)
dht_device = adafruit_dht.DHT11(board.D15, use_pulseio=False)

while True:
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        print(f"Temp: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
    except Exception as e:
        print("Sensor read error:", e)
    time.sleep(2)

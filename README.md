this is the folder structure of raspberry pi
/home/pi/my_device_app/
│
├── startup.py            # Boot entry — decides pairing vs main
├── pairing.py            # Terminal QR pairing flow
├── main.py               # Main process: DHT11, schedule engine, GPIO control, uploads
├── utils.py              # Helper: MAC, config IO, HTTP wrappers, logging helpers
├── config.json           # Local persisted config (created/updated at runtime)
└── logs/
    └── app.log           # App logs (systemd routes stdout/stderr here)

The stuff inside the current json config is just example we will need to populate it with the proper json payload I have the other json expected results in the comments of the files

in order to use the systemd you'll need to create this file in py
raspi-service.service (systemd unit)
Path: /etc/systemd/system/raspi-service.service
[Unit]
Description=My Device App - startup controller (pairing/main)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/my_device_app
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/pi/my_device_app/startup.py
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/pi/my_device_app/logs/app.log
StandardError=append:/home/pi/my_device_app/logs/app.log

[Install]
WantedBy=multi-user.target

Enable & start: (in terminal)
sudo systemctl daemon-reload
sudo systemctl enable raspi-service.service
sudo systemctl start raspi-service.service
sudo journalctl -u raspi-service.service -f
#!/bin/bash
cd /opt/veil_os/organs
for dir in */; do
    organ=$(basename "$dir")
    [ -f "/etc/systemd/system/veil-$organ.service" ] && continue
    
    sudo tee "/etc/systemd/system/veil-$organ.service" > /dev/null << SVC
[Unit]
Description=VeilCore: $organ
[Service]
ExecStart=/usr/bin/python3 /opt/veil_os/organs/$organ/$organ.py
Restart=always
[Install]
WantedBy=multi-user.target
SVC
done
sudo systemctl daemon-reload
for svc in /etc/systemd/system/veil-*.service; do
    sudo systemctl enable $(basename $svc) 2>/dev/null
    sudo systemctl start $(basename $svc) 2>/dev/null
done
sleep 3
systemctl list-units 'veil-*.service' --state=active | grep -c veil-

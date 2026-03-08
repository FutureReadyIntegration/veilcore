#!/bin/bash

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Restarting all Veil OS organs..."
for svc in /etc/systemd/system/*.service; do
    name=$(basename "$svc")
    if [[ "$name" == *".service" ]]; then
        echo "Restarting $name..."
        sudo systemctl restart "$name"
    fi
done

echo "All organs restarted."

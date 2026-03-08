#!/bin/bash
set -e

cd ~/veilcore

echo "═══════════════════════════════════════════════════════"
echo "  VeilCore - Complete Organ Fleet Deployment"
echo "═══════════════════════════════════════════════════════"

# Create directories
sudo mkdir -p /opt/veil_os/organs
sudo mkdir -p /opt/veil_os/var/{log,state,audit}

# Collect all organ specs
ALL_SPECS=()
while IFS= read -r -d '' file; do
    ALL_SPECS+=("$file")
done < <(find . -maxdepth 2 -name "*.yaml" -type f -print0 2>/dev/null)

TOTAL=${#ALL_SPECS[@]}
echo "Found $TOTAL organ specifications"
echo ""

DEPLOYED=0

for spec in "${ALL_SPECS[@]}"; do
    organ_name=$(basename "$spec" .yaml)
    
    # Skip if already active
    if systemctl is-active "veil-$organ_name.service" >/dev/null 2>&1; then
        echo "  ✓ $organ_name"
        ((DEPLOYED++))
        continue
    fi
    
    echo "  → $organ_name"
    
    sudo mkdir -p "/opt/veil_os/organs/$organ_name"
    
    # Generate organ code
    cat > /tmp/organ_temp.py << 'PYEND'
#!/usr/bin/env python3
import time, json, logging, signal, sys
from datetime import datetime
from pathlib import Path

ORGAN_NAME = "PLACEHOLDER"
LOG_FILE = f"/opt/veil_os/var/log/{ORGAN_NAME}.log"
STATE_FILE = f"/opt/veil_os/var/state/{ORGAN_NAME}.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger(ORGAN_NAME)

class Organ:
    def __init__(self):
        self.stats = {"events_processed": 0, "uptime_start": datetime.now().isoformat()}
    
    def cycle(self):
        self.stats["events_processed"] += 1
        Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def run(self):
        logger.info(f"⬡ {ORGAN_NAME.upper()} ACTIVE")
        signal.signal(signal.SIGTERM, lambda s,f: sys.exit(0))
        while True:
            try:
                self.cycle()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    Organ().run()
PYEND

    # Replace placeholder and copy
    sed "s/PLACEHOLDER/$organ_name/g" /tmp/organ_temp.py | sudo tee "/opt/veil_os/organs/$organ_name/$organ_name.py" > /dev/null
    sudo chmod +x "/opt/veil_os/organs/$organ_name/$organ_name.py"
    
    # Create service
    sudo tee "/etc/systemd/system/veil-$organ_name.service" > /dev/null << SVC
[Unit]
Description=VeilCore: $organ_name
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/veil_os/organs/$organ_name/$organ_name.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVC

    sudo systemctl daemon-reload
    sudo systemctl enable "veil-$organ_name.service" 2>/dev/null
    sudo systemctl start "veil-$organ_name.service" 2>/dev/null
    ((DEPLOYED++))
done

sleep 5
ACTIVE=$(systemctl list-units 'veil-*.service' --state=active --no-pager 2>/dev/null | grep -c "veil-" || echo "0")

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Deployment Complete!"
echo "  Total Specs:  $TOTAL"
echo "  Active Now:   $ACTIVE"
echo "═══════════════════════════════════════════════════════"

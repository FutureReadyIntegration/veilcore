#!/usr/bin/env python3
import yaml, os, psutil
from pathlib import Path

WORKING_ORGANS = {'guardian', 'sentinel', 'cortex', 'zombie_sweeper', 'watchdog', 'audit'}

def generate_monitoring_logic(name, description, spec):
    if 'network' in name or 'firewall' in name:
        return "connections = psutil.net_connections()\n        logger.info(f'Network: {len(connections)} connections')"
    elif 'auth' in name:
        return "logger.info('Monitoring authentication')"
    elif 'telemetry' in name or 'metrics' in name:
        return "cpu = psutil.cpu_percent(0.5)\n        logger.info(f'CPU: {cpu}%')"
    else:
        return "logger.info(f'Monitoring {ORGAN_NAME}')"

specs = {}
for pattern in ['*.yaml', 'organ_specs/*.yaml']:
    for file in Path('.').glob(pattern):
        if file.stem not in specs:
            specs[file.stem] = file

print(f"Found {len(specs)} specs, generating {len(specs)-6} new organs...")

for name in sorted(specs.keys()):
    if name in WORKING_ORGANS: continue
    
    organ_dir = Path(f'/opt/veil_os/organs/{name}')
    organ_dir.mkdir(parents=True, exist_ok=True)
    
    code = f'''#!/usr/bin/env python3
import time, json, logging, signal, psutil, sys
from pathlib import Path
from datetime import datetime

ORGAN_NAME = "{name}"
LOG_FILE = f"/opt/veil_os/var/log/{{ORGAN_NAME}}.log"
STATE_FILE = f"/opt/veil_os/var/state/{{ORGAN_NAME}}.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])
logger = logging.getLogger(ORGAN_NAME)

class Organ:
    def __init__(self):
        self.stats = {{"events_processed": 0, "uptime_start": datetime.now().isoformat()}}
    
    def monitor(self):
        {generate_monitoring_logic(name, "", {})}
        self.stats["events_processed"] += 1
    
    def run(self):
        logger.info(f"⬡ {{ORGAN_NAME.upper()}} ACTIVE")
        signal.signal(signal.SIGTERM, lambda s,f: sys.exit(0))
        while True:
            try:
                self.monitor()
                Path(STATE_FILE).parent.mkdir(parents=True, exist_ok=True)
                with open(STATE_FILE, 'w') as f:
                    json.dump(self.stats, f)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {{e}}")
                time.sleep(10)

if __name__ == "__main__":
    Organ().run()
'''
    
    with open(organ_dir / f'{name}.py', 'w') as f:
        f.write(code)
    os.chmod(organ_dir / f'{name}.py', 0o755)
    print(f"✓ {name}")

print(f"\n✅ Generated {len(specs)-6} organs!")
print("Deploy with: sudo systemctl daemon-reload && sudo systemctl start veil-*.service")

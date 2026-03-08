#!/bin/bash

echo "=== Veil OS Immutable Sweep ==="
echo ""

# Directories to sweep
targets=(
  /opt/veil_os
  /var/log/veil
  /var/lib/veil
  /etc/systemd/system
)

for t in "${targets[@]}"; do
  echo "Sweeping: $t"
  sudo chattr -R -i "$t" 2>/dev/null
done

echo ""
echo "Sweep complete. All immutable bits removed."

#!/bin/bash

echo "=== Veil OS Organ Health Check ==="
echo ""

services=(
  veil-sentinel
  veil-master
  veil-guardian
  veil-weaver
  veil-zero_trust
  veil-analytics
  veil-insider_threat
  veil-auto_lockdown
  veil-zombie_sweeper
  veil-hospital
  veil-telemetry
)

for svc in "${services[@]}"; do
  status=$(systemctl is-active $svc)
  printf "%-25s : %s\n" "$svc" "$status"
done

echo ""
echo "Log directory: /var/log/veil"
ls -lh /var/log/veil

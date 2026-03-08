#!/bin/bash
echo "🚨 Compiling P0 Critical Organs..."

for organ in epic imprivata backup quarantine; do
  echo "→ $organ"
  veilc create /opt/veil_os/organ_specs/${organ}.yaml
  veilc activate $organ
done

echo "✅ P0 organs deployed."
veilc list | grep -E "epic|imprivata|backup|quarantine"

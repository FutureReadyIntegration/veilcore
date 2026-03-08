#!/bin/bash

# Veil OS: Activate all organ specs

echo "🩺 Activating all organ specs..."

for spec in /opt/veil_os/organ_specs/*.yaml; do
    echo "→ Compiling $(basename "$spec")"
    veilc create "$spec"
done

echo "✅ All organs compiled."

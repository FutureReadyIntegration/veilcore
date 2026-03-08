#!/bin/bash
echo "🧠 Compiling and activating all organ specs..."

shopt -s nullglob
specs=(/opt/veil_os/organ_specs/*.yaml)

if [ ${#specs[@]} -eq 0 ]; then
  echo "⚠️  No spec files found."
  exit 1
fi

compiled=0
activated=0
failed=0

for spec in "${specs[@]}"; do
  name=$(basename "$spec" .yaml)
  echo "→ $name"
  
  if veilc create "$spec"; then
    ((compiled++))
    if veilc activate "$name"; then
      ((activated++))
    else
      ((failed++))
    fi
  else
    ((failed++))
  fi
done

echo ""
echo "✅ Done: $compiled compiled, $activated activated, $failed failed."
[ $failed -gt 0 ] && exit 1 || exit 0

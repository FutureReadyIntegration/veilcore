#!/bin/bash
echo "🧠 Compiling all organ specs..."

shopt -s nullglob
specs=(/opt/veil_os/organ_specs/*.yaml)

if [ ${#specs[@]} -eq 0 ]; then
  echo "⚠️  No spec files found."
  exit 1
fi

failed=0
succeeded=0

for spec in "${specs[@]}"; do
  name=$(basename "$spec" .yaml)
  echo "→ $name"
  
  if veilc create "$spec"; then
    ((succeeded++))
  else
    ((failed++))
  fi
done

echo ""
echo "✅ Done: $succeeded succeeded, $failed failed."
[ $failed -gt 0 ] && exit 1 || exit 0

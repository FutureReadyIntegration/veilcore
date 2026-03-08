#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "  Finding Duplicate Organ Specs"
echo "═══════════════════════════════════════════════════════"
echo ""

# Get all YAML files
declare -A seen
duplicates=()

for file in *.yaml organ_specs/*.yaml 2>/dev/null; do
    [ -f "$file" ] || continue
    
    name=$(basename "$file" .yaml)
    
    if [ -n "${seen[$name]}" ]; then
        echo "DUPLICATE: $name"
        echo "  First:  ${seen[$name]}"
        echo "  Second: $file"
        duplicates+=("$file")
        echo ""
    else
        seen[$name]="$file"
    fi
done

echo "═══════════════════════════════════════════════════════"
echo "Total unique organs: ${#seen[@]}"
echo "Total duplicates: ${#duplicates[@]}"
echo "═══════════════════════════════════════════════════════"

if [ ${#duplicates[@]} -gt 0 ]; then
    echo ""
    echo "Remove duplicates? (y/n)"
    read -r response
    
    if [[ "$response" == "y" ]]; then
        for dup in "${duplicates[@]}"; do
            echo "Removing: $dup"
            rm "$dup"
        done
        echo ""
        echo "✓ Duplicates removed!"
        echo "Remaining specs: $(find . -maxdepth 2 -name "*.yaml" -type f | wc -l)"
    fi
fi

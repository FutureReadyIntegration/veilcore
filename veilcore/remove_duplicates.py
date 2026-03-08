#!/usr/bin/env python3
import os
from pathlib import Path

print("=" * 60)
print("  Finding Duplicate Organ Specs")
print("=" * 60)
print()

# Find all YAML files
yaml_files = []
for pattern in ['*.yaml', 'organ_specs/*.yaml']:
    yaml_files.extend(Path('.').glob(pattern))

# Track by basename
seen = {}
duplicates = []

for file in yaml_files:
    name = file.stem  # filename without extension
    
    if name in seen:
        print(f"DUPLICATE: {name}")
        print(f"  Keep:   {seen[name]}")
        print(f"  Remove: {file}")
        duplicates.append(file)
        print()
    else:
        seen[name] = file

print("=" * 60)
print(f"Unique organs: {len(seen)}")
print(f"Duplicates: {len(duplicates)}")
print("=" * 60)

if duplicates:
    print()
    response = input("Remove duplicates? (y/n): ")
    
    if response.lower() == 'y':
        for dup in duplicates:
            print(f"Removing: {dup}")
            dup.unlink()
        
        print()
        print(f"✓ Removed {len(duplicates)} duplicates!")
        
        remaining = len(list(Path('.').glob('*.yaml'))) + len(list(Path('.').glob('organ_specs/*.yaml')))
        print(f"Remaining specs: {remaining}")

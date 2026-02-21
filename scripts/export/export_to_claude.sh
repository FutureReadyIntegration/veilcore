#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTDIR="assets/exports/veilcore-export-$STAMP"
TARBALL="assets/exports/veilcore-export-$STAMP.tar.gz"

mkdir -p "$OUTDIR"

FILES=(
  # Docs
  "README.md"

  # API Gate Fix (confirmed by your grep)
  "veil/api.py"

  # SOC assets
  "assets/banners/readme-header.svg"
  "assets/banners/readme-header.png"
  "assets/banners/architecture.svg"
  "assets/banners/architecture.gif"

  # Plaques
  "assets/badges/invariant-plaque.svg"
  "assets/badges/security-plaque.svg"

  # Helper scripts
  "scripts/sync_readme_organs.py"
  "scripts/export/rebuild_arch_gif.py"
)

echo "[*] Copying into: $OUTDIR"
for f in "${FILES[@]}"; do
  if [[ -e "$f" ]]; then
    mkdir -p "$OUTDIR/$(dirname "$f")"
    cp -a "$f" "$OUTDIR/$f"
    echo "    [+] $f"
  else
    echo "    [-] missing (skipped): $f"
  fi
done

cat > "$OUTDIR/MANIFEST.md" <<EOF
# VeilCore Export Bundle

Generated: $STAMP (UTC)
Commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")

Included:
$(printf -- "- %s\n" "${FILES[@]}")

Apply:
  ./APPLY.sh /path/to/veilcore
Optional GIF rebuild:
  ./APPLY.sh /path/to/veilcore --rebuild-gif
EOF

cat > "$OUTDIR/APPLY.sh" <<'APPLY'
#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-}"
FLAG="${2:-}"

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 /path/to/veilcore [--rebuild-gif]"
  exit 1
fi
if [[ ! -d "$TARGET/.git" ]]; then
  echo "ERROR: target must be a git repo (missing .git): $TARGET"
  exit 1
fi

cd "$TARGET"

copy_if_present() {
  local rel="$1"
  if [[ -e "$BUNDLE_DIR/$rel" ]]; then
    mkdir -p "$(dirname "$rel")"
    cp -a "$BUNDLE_DIR/$rel" "$rel"
    echo "    [+] applied: $rel"
  fi
}

echo "[*] Applying bundle -> $(pwd)"

copy_if_present "README.md"
copy_if_present "veil/api.py"

copy_if_present "assets/banners/readme-header.svg"
copy_if_present "assets/banners/readme-header.png"
copy_if_present "assets/banners/architecture.svg"
copy_if_present "assets/banners/architecture.gif"

copy_if_present "assets/badges/invariant-plaque.svg"
copy_if_present "assets/badges/security-plaque.svg"

copy_if_present "scripts/sync_readme_organs.py"
copy_if_present "scripts/export/rebuild_arch_gif.py"

echo
echo "[*] Sanity check: compile API"
python3 -m py_compile veil/api.py && echo "    [✓] veil/api.py syntax OK"

if [[ "$FLAG" == "--rebuild-gif" ]]; then
  echo
  echo "[*] Rebuilding architecture.gif from architecture.svg"
  python3 scripts/export/rebuild_arch_gif.py \
    --svg assets/banners/architecture.svg \
    --gif assets/banners/architecture.gif \
    --frames 36 \
    --duration 0.06
fi

echo
echo "[*] Done. Review:"
echo "    git status"
echo
echo "[*] Commit:"
echo "    git add -A"
echo "    git commit -m \"Apply VeilCore API gate fix + SOC assets + plaques\""
APPLY
chmod +x "$OUTDIR/APPLY.sh"

echo "[*] Creating tarball: $TARBALL"
tar -czf "$TARBALL" -C "$OUTDIR" .

echo
echo "[✓] Export created:"
echo "    $TARBALL"

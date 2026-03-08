#!/usr/bin/env bash
set -uo pipefail


# Must run as root
if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo bash $0"
  exit 1
fi
# -----------------------------
# Veil "redo" program
# Repairs venv + /opt/veil_env + systemd env files for API + firewall keys
# -----------------------------

VENV="/opt/veil_os/venv"
ENV_LINK="/opt/veil_env"

MSOS_SVC="veilcore-msos.service"
API_SVC="veil-api.service"

API_DROPIN_DIR="/etc/systemd/system/${API_SVC}.d"
MSOS_DROPIN_DIR="/etc/systemd/system/${MSOS_SVC}.d"

# ---------- helpers ----------
log() { echo -e "\n==> $*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

# ---------- preflight ----------
need_cmd python3
need_cmd systemctl
need_cmd sed
need_cmd awk

log "0/8 Create or repair venv at ${VENV}"
if [[ ! -x "${VENV}/bin/python" ]]; then
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi

log "1/8 Make /opt/veil_env point to venv (${VENV})"
if [[ -e "$ENV_LINK" || -L "$ENV_LINK" ]]; then
  rm -rf "$ENV_LINK"
fi
ln -s "$VENV" "$ENV_LINK"

log "2/8 Ensure venv pip tooling is healthy"
"${ENV_LINK}/bin/python" -m pip install --upgrade --no-cache-dir pip setuptools wheel >/dev/null

log "3/8 Hard reset uvicorn/fastapi stack"
SITEPKG="$("${ENV_LINK}/bin/python" - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"

if [[ -f "/home/user/veilcore/uvicorn.py" || -f "/home/user/veilcore/uvicorn/__init__.py" ]]; then
  echo "WARNING: Local uvicorn.py or uvicorn/ folder may shadow the package."
fi

rm -rf "${SITEPKG}/uvicorn" "${SITEPKG}/uvicorn-"* "${SITEPKG}/uvicorn"*.dist-info 2>/dev/null || true

"${ENV_LINK}/bin/python" -m pip install --no-cache-dir --upgrade \
  "fastapi==0.110.0" \
  "uvicorn==0.30.1" \
  "pydantic==2.6.4" \
  "starlette==0.36.3" \
  "cryptography==42.0.8"

log "4/8 Verify imports from venv"
"${ENV_LINK}/bin/python" - <<'PY'
import fastapi, uvicorn, cryptography
import uvicorn.main
print("OK imports:",
      "fastapi", fastapi.__version__,
      "uvicorn", uvicorn.__version__,
      "cryptography", cryptography.__version__)
PY

log "5/8 Fix MSOS policy keys drop-in quoting (FERNET line)"
mkdir -p "$MSOS_DROPIN_DIR"
POLICY_CONF="${MSOS_DROPIN_DIR}/30-policy-keys.conf"

if [[ -f "$POLICY_CONF" ]]; then
  sed -i \
    -e 's/^Environment="VEIL_POLICY_FERNET="/# (deprecated) removed broken VEIL_POLICY_FERNET line: /' \
    -e 's/^Environment="VEIL_POLICY_FERNET_KEY="\([^"]*\)""/Environment="VEIL_POLICY_FERNET_KEY=\1"/' \
    "$POLICY_CONF" || true
fi

log "6/8 Fix API key drop-in formatting"
mkdir -p "$API_DROPIN_DIR"
APIKEY_CONF="${API_DROPIN_DIR}/60-api-key.conf"

if [[ -f "$APIKEY_CONF" ]]; then
  RAW_KEY="$(grep -Eo '[0-9a-f]{32,128}' "$APIKEY_CONF" | head -n1 || true)"
  if [[ -n "$RAW_KEY" ]]; then
    cat > "$APIKEY_CONF" <<INNER
[Service]
Environment="VEIL_API_KEY=${RAW_KEY}"
INNER
  fi
fi

log "7/8 Ensure veil-api ExecStart points to /opt/veil_env"
cat > "${API_DROPIN_DIR}/50-execstart.conf" <<'INNER'
[Service]
ExecStart=
ExecStart=/opt/veil_env/bin/uvicorn veil.api:app --host 127.0.0.1 --port 9444
INNER

log "8/8 Reload systemd and restart services"
systemctl daemon-reload
systemctl reset-failed "$MSOS_SVC" "$API_SVC" 2>/dev/null || true

systemctl restart "$MSOS_SVC" || echo "WARN: $MSOS_SVC failed to restart"
systemctl restart "$API_SVC" || echo "WARN: $API_SVC failed to restart"

log "Status:"
systemctl is-active "$MSOS_SVC" "$API_SVC" || true
systemctl status "$API_SVC" --no-pager -l | sed -n '1,25p' || true

log "Quick health test"
API_KEY="$(systemctl show -p Environment "$API_SVC" | tr ' ' '\n' | sed -n 's/^Environment=VEIL_API_KEY=//p' | tr -d '"')"
if [[ -n "${API_KEY:-}" ]]; then
  echo "API_KEY detected (len=${#API_KEY}). Hitting /health..."
  curl -sS http://127.0.0.1:9444/health -H "X-API-Key: ${API_KEY}" || true
  echo
else
  echo "No VEIL_API_KEY found in systemd env; set ${APIKEY_CONF} then restart veil-api."
fi

log "DONE"

#!/usr/bin/env bash
set -e

APP_NAME="veil_os"
APP_USER="veil"
APP_GROUP="veil"
APP_DIR="/opt/veil_os"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE="/etc/systemd/system/veil.service"
VERSION_FILE="$APP_DIR/VERSION"

echo "[veil] Starting Veil OS installer..."

if [ "$(id -u)" -ne 0 ]; then
    echo "[veil] Please run this script as root (use: sudo bash install_veil.sh)"
    exit 1
fi

echo "[veil] Installing system dependencies..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip curl rsync

if ! id "$APP_USER" >/dev/null 2>&1; then
    echo "[veil] Creating system user: $APP_USER"
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
fi

echo "[veil] Creating application directory at $APP_DIR..."
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR" || true

SRC_DIR="$(pwd)"
echo "[veil] Copying Veil OS source from $SRC_DIR to $APP_DIR..."
rsync -a --delete "$SRC_DIR"/ "$APP_DIR"/

echo "[veil] Creating Python virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"

echo "[veil] Upgrading pip and installing Veil OS..."
"$VENV_DIR/bin/pip" install --upgrade pip
cd "$APP_DIR"
"$VENV_DIR/bin/pip" install -e .

if [ ! -f "$VERSION_FILE" ]; then
    echo "[veil] Creating VERSION file..."
    echo "0.1.0" > "$VERSION_FILE"
fi

echo "[veil] Writing systemd service file to $SERVICE_FILE..."

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Veil Hospital Control Plane
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$APP_DIR
ExecStart=$VENV_DIR/bin/python3 $APP_DIR/veil/hospital_gui/main.py
Restart=on-failure
RestartSec=5
LimitNOFILE=65536
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

echo "[veil] Reloading systemd daemon..."
systemctl daemon-reload

echo "[veil] Enabling veil.service..."
systemctl enable veil.service

echo "[veil] Starting veil.service..."
systemctl restart veil.service

echo "[veil] Checking veil.service status..."
systemctl status veil.service --no-pager || true

echo "[veil] Waiting for service to come up..."
sleep 2

echo "[veil] Probing /health..."
curl -fsS http://127.0.0.1:8000/health || curl -fsS http://127.0.0.1:5000/health || true

echo "[veil] Veil OS installation complete."

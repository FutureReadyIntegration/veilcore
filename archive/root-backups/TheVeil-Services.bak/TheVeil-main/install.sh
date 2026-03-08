#!/bin/bash
#
# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║   THE VEIL - Installation Script                                              ║
# ║   Hospital Cybersecurity Platform                                             ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝
#
# Usage: sudo ./install.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   THE VEIL - Hospital Cybersecurity Platform                                  ║${NC}"
echo -e "${BLUE}║   Installation Script v1.0                                                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./install.sh)${NC}"
    exit 1
fi

# Detect installation directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/veil_os"
VEIL_USER="veil"
VEIL_GROUP="veil"

echo -e "${YELLOW}[1/8] Creating system user...${NC}"
if ! id "$VEIL_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false "$VEIL_USER"
    echo -e "${GREEN}  ✓ Created user: $VEIL_USER${NC}"
else
    echo -e "${GREEN}  ✓ User $VEIL_USER already exists${NC}"
fi

echo -e "${YELLOW}[2/8] Creating directories...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/lib/veil/security
mkdir -p /var/lib/veil/audit
mkdir -p /var/lib/veil/zero_trust
mkdir -p /var/lib/veil/sentinel
mkdir -p /var/lib/veil/insider_threat
mkdir -p /var/lib/veil/lockdown
mkdir -p /var/log/veil
mkdir -p /etc/veil
echo -e "${GREEN}  ✓ Directories created${NC}"

echo -e "${YELLOW}[3/8] Copying files...${NC}"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
echo -e "${GREEN}  ✓ Files copied to $INSTALL_DIR${NC}"

echo -e "${YELLOW}[4/8] Setting permissions...${NC}"
chown -R "$VEIL_USER:$VEIL_GROUP" /var/lib/veil
chown -R "$VEIL_USER:$VEIL_GROUP" /var/log/veil
chmod 700 /var/lib/veil/security
chmod 700 /var/lib/veil/audit
chmod 600 /var/lib/veil/security/* 2>/dev/null || true
echo -e "${GREEN}  ✓ Permissions set${NC}"

echo -e "${YELLOW}[5/8] Installing Python dependencies...${NC}"
if command -v pip3 &>/dev/null; then
    pip3 install fastapi uvicorn jinja2 python-multipart aiofiles --quiet
    echo -e "${GREEN}  ✓ Python dependencies installed${NC}"
else
    echo -e "${RED}  ✗ pip3 not found - please install Python 3 and pip${NC}"
    exit 1
fi

echo -e "${YELLOW}[6/8] Installing systemd service...${NC}"
cat > /etc/systemd/system/veil.service << 'EOF'
[Unit]
Description=The Veil - Hospital Cybersecurity Platform
After=network.target

[Service]
Type=simple
User=veil
Group=veil
WorkingDirectory=/opt/veil_os
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="VEIL_HOST=127.0.0.1"
Environment="VEIL_PORT=8000"
ExecStart=/usr/bin/python3 -m uvicorn veil.hospital_gui.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/veil /var/log/veil

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
echo -e "${GREEN}  ✓ Systemd service installed${NC}"

echo -e "${YELLOW}[7/8] Creating configuration file...${NC}"
if [ ! -f /etc/veil/config.env ]; then
    cat > /etc/veil/config.env << 'EOF'
# The Veil Configuration
# ======================

# Server settings
VEIL_HOST=127.0.0.1
VEIL_PORT=8000
VEIL_DEBUG=false

# Security settings
VEIL_SECRET_KEY=  # Leave empty to auto-generate
VEIL_SESSION_TIMEOUT=60
VEIL_MAX_FAILED_ATTEMPTS=5

# Paths
VEIL_DATA_DIR=/var/lib/veil
VEIL_LOG_DIR=/var/log/veil
EOF
    chmod 600 /etc/veil/config.env
    echo -e "${GREEN}  ✓ Configuration file created at /etc/veil/config.env${NC}"
else
    echo -e "${GREEN}  ✓ Configuration file already exists${NC}"
fi

echo -e "${YELLOW}[8/8] Starting service...${NC}"
systemctl enable veil.service
systemctl start veil.service

# Wait for startup
sleep 3

if systemctl is-active --quiet veil.service; then
    echo -e "${GREEN}  ✓ Service started successfully${NC}"
else
    echo -e "${RED}  ✗ Service failed to start - check: journalctl -u veil.service${NC}"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation Complete!                                                      ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Access:${NC}       http://127.0.0.1:8000"
echo -e "  ${BLUE}Username:${NC}     admin"
echo -e "  ${BLUE}Password:${NC}     VeilAdmin2024!"
echo ""
echo -e "  ${RED}⚠️  IMPORTANT: Change the default password immediately!${NC}"
echo ""
echo -e "  ${YELLOW}Useful commands:${NC}"
echo -e "    systemctl status veil        # Check status"
echo -e "    systemctl restart veil       # Restart service"
echo -e "    journalctl -u veil -f        # View logs"
echo ""

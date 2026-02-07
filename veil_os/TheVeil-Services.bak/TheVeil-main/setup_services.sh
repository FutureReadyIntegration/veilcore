#!/bin/bash
#
# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║   THE VEIL - Service Setup Script                                             ║
# ║   Installs systemd services and veilctl                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   THE VEIL - Service Setup                                                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./setup_services.sh)${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/veil_os"
SYSTEMD_DIR="/etc/systemd/system"

echo -e "${YELLOW}[1/6] Copying updated files to ${INSTALL_DIR}...${NC}"
cp -r "$SCRIPT_DIR/veil/"* "$INSTALL_DIR/veil/" 2>/dev/null || true
echo -e "${GREEN}  ✓ Files updated${NC}"

echo -e "${YELLOW}[2/6] Creating data directories...${NC}"
mkdir -p /var/lib/veil/{security,audit,sentinel,insider_threat,lockdown,zero_trust}
mkdir -p /var/log/veil
chown -R user:user /var/lib/veil /var/log/veil 2>/dev/null || true
chmod 755 /var/lib/veil
chmod 755 /var/log/veil
echo -e "${GREEN}  ✓ Directories ready${NC}"

echo -e "${YELLOW}[3/6] Installing systemd services...${NC}"

# Main Veil API service
cat > $SYSTEMD_DIR/veil.service << 'EOF'
[Unit]
Description=The Veil - Hospital Cybersecurity Platform (API)
After=network.target
Wants=veil-sentinel.service veil-insider-threat.service veil-auto-lockdown.service veil-zero-trust.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/opt/veil_os
Environment="PYTHONPATH=/opt/veil_os"
Environment="VEIL_HOST=127.0.0.1"
Environment="VEIL_PORT=8000"
ExecStart=/opt/veil_os/api_venv/bin/python -m uvicorn veil.hospital_gui.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
ReadWritePaths=/var/lib/veil /var/log/veil

[Install]
WantedBy=multi-user.target
EOF

# Sentinel service
cat > $SYSTEMD_DIR/veil-sentinel.service << 'EOF'
[Unit]
Description=The Veil - Sentinel (Behavioral Anomaly Detection)
After=network.target
PartOf=veil.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/opt/veil_os
Environment="PYTHONPATH=/opt/veil_os"
ExecStart=/opt/veil_os/api_venv/bin/python -m veil.organ_runner sentinel
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
ReadWritePaths=/var/lib/veil/sentinel /var/log/veil

[Install]
WantedBy=veil.service
EOF

# Insider Threat service
cat > $SYSTEMD_DIR/veil-insider-threat.service << 'EOF'
[Unit]
Description=The Veil - Insider Threat Detector
After=network.target
PartOf=veil.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/opt/veil_os
Environment="PYTHONPATH=/opt/veil_os"
ExecStart=/opt/veil_os/api_venv/bin/python -m veil.organ_runner insider_threat
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
ReadWritePaths=/var/lib/veil/insider_threat /var/log/veil

[Install]
WantedBy=veil.service
EOF

# Auto-Lockdown service (P0 - faster restart)
cat > $SYSTEMD_DIR/veil-auto-lockdown.service << 'EOF'
[Unit]
Description=The Veil - Auto-Lockdown Engine (Automated Response)
After=network.target
PartOf=veil.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/opt/veil_os
Environment="PYTHONPATH=/opt/veil_os"
ExecStart=/opt/veil_os/api_venv/bin/python -m veil.organ_runner auto_lockdown
Restart=always
RestartSec=5
StartLimitIntervalSec=120
StartLimitBurst=10
ReadWritePaths=/var/lib/veil/lockdown /var/log/veil

[Install]
WantedBy=veil.service
EOF

# Zero-Trust service
cat > $SYSTEMD_DIR/veil-zero-trust.service << 'EOF'
[Unit]
Description=The Veil - Zero-Trust Engine (Continuous Verification)
After=network.target
PartOf=veil.service

[Service]
Type=simple
User=user
Group=user
WorkingDirectory=/opt/veil_os
Environment="PYTHONPATH=/opt/veil_os"
ExecStart=/opt/veil_os/api_venv/bin/python -m veil.organ_runner zero_trust
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
ReadWritePaths=/var/lib/veil/zero_trust /var/log/veil

[Install]
WantedBy=veil.service
EOF

echo -e "${GREEN}  ✓ Services installed${NC}"

echo -e "${YELLOW}[4/6] Installing veilctl...${NC}"
cp "$SCRIPT_DIR/veilctl" /usr/local/bin/veilctl
chmod +x /usr/local/bin/veilctl
echo -e "${GREEN}  ✓ veilctl installed to /usr/local/bin/veilctl${NC}"

echo -e "${YELLOW}[5/6] Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}  ✓ Systemd reloaded${NC}"

echo -e "${YELLOW}[6/6] Enabling services...${NC}"
systemctl enable veil.service
systemctl enable veil-sentinel.service
systemctl enable veil-insider-threat.service
systemctl enable veil-auto-lockdown.service
systemctl enable veil-zero-trust.service
echo -e "${GREEN}  ✓ Services enabled${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup Complete!                                                             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BLUE}Start all services:${NC}"
echo "    sudo systemctl start veil"
echo ""
echo -e "  ${BLUE}Or use veilctl:${NC}"
echo "    veilctl start all"
echo "    veilctl status"
echo "    veilctl health"
echo ""
echo -e "  ${BLUE}Available commands:${NC}"
echo "    veilctl status              # Show all organ status"
echo "    veilctl start [organ]       # Start organ or all"
echo "    veilctl stop [organ]        # Stop organ or all"
echo "    veilctl restart [organ]     # Restart organ or all"
echo "    veilctl logs <organ> [n]    # View organ logs"
echo "    veilctl health              # Health check"
echo "    veilctl patients            # Patient stats"
echo "    veilctl audit [n]           # Recent audit events"
echo ""
echo -e "  ${BLUE}Services installed:${NC}"
echo "    veil.service                # Main API"
echo "    veil-sentinel.service       # Anomaly detection"
echo "    veil-insider-threat.service # Insider threat"
echo "    veil-auto-lockdown.service  # Auto response"
echo "    veil-zero-trust.service     # Zero trust"
echo ""
echo -e "  ${YELLOW}Self-healing:${NC} All services auto-restart on failure"
echo ""

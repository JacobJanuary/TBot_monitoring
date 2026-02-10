#!/bin/bash
# ─────────────────────────────────────────────────────────
# Fox Monitor Dashboard — Ubuntu Server Setup
# Run from: /home/elcrypto/TBot_monitoring/monitor_ui
# ─────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/home/elcrypto/TBot_monitoring/monitor_ui"
SERVICE_NAME="fox-monitor"

echo "═══ Fox Monitor Dashboard — Setup ═══"

# ── 1. System dependencies ───────────────────────────────
echo "→ Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip

# ── 2. Virtual environment ──────────────────────────────
echo "→ Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# ── 3. .env file ─────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "→ Creating .env (edit with your DB credentials)..."
    cat > "$INSTALL_DIR/.env" << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fox_crypto
DB_USER=your_db_user
DB_PASSWORD=your_db_password
EOF
    echo "  ⚠️  Edit $INSTALL_DIR/.env with actual DB credentials!"
fi

# ── 4. Install systemd service ──────────────────────────
echo "→ Installing systemd service..."
sudo cp "$INSTALL_DIR/deploy/fox-monitor.service" /etc/systemd/system/"$SERVICE_NAME".service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "═══ Done! ═══"
echo "  1. Edit DB creds:    nano $INSTALL_DIR/.env"
echo "  2. Start service:    sudo systemctl start $SERVICE_NAME"
echo "  3. Check status:     sudo systemctl status $SERVICE_NAME"
echo "  4. View logs:        sudo journalctl -u $SERVICE_NAME -f"
echo "  5. SSH tunnel:       ssh -L 8080:localhost:8080 elcrypto@SERVER"
echo "  6. Open browser:     http://localhost:8080"
echo ""

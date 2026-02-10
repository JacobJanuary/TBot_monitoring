#!/bin/bash
# ─────────────────────────────────────────────────────────
# Fox Monitor Dashboard — Ubuntu Server Deploy Script
# ─────────────────────────────────────────────────────────
set -euo pipefail

INSTALL_DIR="/opt/monitor_ui"
SERVICE_NAME="fox-monitor"
SERVICE_USER="trading"

echo "═══ Fox Monitor Dashboard — Deployer ═══"
echo ""

# ── 1. System dependencies ───────────────────────────────
echo "→ Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip

# ── 2. Create service user (if missing) ─────────────────
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "→ Creating user '$SERVICE_USER'..."
    sudo useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
fi

# ── 3. Copy files ────────────────────────────────────────
echo "→ Installing to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo rsync -a --exclude='venv/' --exclude='*.pyc' --exclude='__pycache__' \
    --exclude='.env' --exclude='*.log' --exclude='deploy/' \
    . "$INSTALL_DIR/"

# ── 4. Virtual environment ──────────────────────────────
echo "→ Setting up Python virtual environment..."
sudo python3 -m venv "$INSTALL_DIR/venv"
sudo "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"

# ── 5. .env file ─────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "→ Creating .env file (edit with your DB credentials)..."
    sudo tee "$INSTALL_DIR/.env" > /dev/null << 'EOF'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fox_crypto
DB_USER=your_db_user
DB_PASSWORD=your_db_password
EOF
    echo ""
    echo "  ⚠️  IMPORTANT: Edit $INSTALL_DIR/.env with your actual DB credentials!"
    echo ""
fi

# ── 6. Set ownership ────────────────────────────────────
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# ── 7. Install systemd service ──────────────────────────
echo "→ Installing systemd service..."
sudo cp deploy/fox-monitor.service /etc/systemd/system/"$SERVICE_NAME".service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo ""
echo "═══ Installation complete! ═══"
echo ""
echo "Next steps:"
echo "  1. Edit DB credentials:   sudo nano $INSTALL_DIR/.env"
echo "  2. Start the service:     sudo systemctl start $SERVICE_NAME"
echo "  3. Check status:          sudo systemctl status $SERVICE_NAME"
echo "  4. View logs:             sudo journalctl -u $SERVICE_NAME -f"
echo "  5. Open in browser:       http://YOUR_SERVER_IP:8080"
echo ""

#!/bin/bash

# Installation script for Fox Crypto Trading Bot Monitor

set -e

echo "=========================================="
echo "Fox Crypto Trading Bot Monitor - Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✓ Python $PYTHON_VERSION found"
else
    echo "✗ Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment already exists"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "✓ pip upgraded"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created (please edit with your database credentials)"
else
    echo "✓ .env file already exists"
fi

# Make main.py executable
chmod +x main.py
echo "✓ main.py made executable"

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your database credentials:"
echo "   nano .env"
echo ""
echo "2. Test database connection:"
echo "   source venv/bin/activate"
echo "   python -c 'import asyncio; from database.connection import DatabasePool; print(asyncio.run(DatabasePool.test_connection()))'"
echo ""
echo "3. Run the monitor:"
echo "   python main.py"
echo ""
echo "For more information, see:"
echo "  - QUICKSTART.md for quick start guide"
echo "  - README.md for full documentation"
echo ""

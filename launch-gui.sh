#!/bin/bash

# Launch script for Awesome Claude Code Admin GUI

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -q flask 'wtforms<3.1'

# Launch the Flask app
echo "Launching Awesome Claude Code Admin GUI..."
echo "Access the admin panel at: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python admin/simple_app.py

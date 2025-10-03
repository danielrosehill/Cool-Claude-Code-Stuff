#!/bin/bash

# Launch script for Awesome Claude Code Admin GUI
# For Ubuntu Linux - Uses uv for venv management

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRIVATE_DIR="$SCRIPT_DIR/private"

# Check if private directory exists
if [ ! -d "$PRIVATE_DIR" ]; then
    echo "Error: private directory not found at $PRIVATE_DIR"
    exit 1
fi

cd "$PRIVATE_DIR"

VENV_DIR=".venv"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed."
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with uv..."
    uv venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Install streamlit if not already installed
if ! python -c "import streamlit" &> /dev/null; then
    echo "Installing streamlit..."
    uv pip install streamlit
fi

# Launch the Streamlit app
echo "Launching Awesome Claude Code Admin GUI..."
echo "The GUI will open in your default browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run admin_gui.py

#!/bin/bash

# Launch the Streamlit admin GUI
cd "$(dirname "$0")/private"
streamlit run admin_gui.py

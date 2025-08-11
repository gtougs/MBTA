#!/bin/bash
# Local Streamlit Dashboard Runner
# This script runs the Streamlit dashboard locally for testing

echo "MBTA Transit Analytics Dashboard - Local Runner"
echo "=============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements_streamlit.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: No .env file found!"
    echo "Please create a .env file with your database configuration:"
    echo "DATABASE_URL=postgresql://mbta_user:mbta_password@localhost:5432/mbta_data"
    echo ""
    echo "You can copy from config.env.example"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run Streamlit dashboard
echo "Starting Streamlit dashboard..."
echo "Dashboard will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop"
echo ""

streamlit run streamlit_dashboard.py --server.port 8501 --server.address 0.0.0.0

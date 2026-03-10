#!/bin/bash
# Double-click this file on Mac to start the Veston Campaign Tool
cd "$(dirname "$0")"

echo ""
echo "======================================"
echo "  Setting up Veston Campaign Tool..."
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python is not installed."
    echo ""
    echo "To install it:"
    echo "  1. Go to python.org/downloads"
    echo "  2. Download the latest version for Mac"
    echo "  3. Run the installer"
    echo "  4. Then double-click this file again"
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

# Install dependencies if needed
python3 -m pip install flask requests python-dotenv --quiet 2>/dev/null

# Check if .env exists
if [ ! -f .env ]; then
    echo "No .env file found. Creating one..."
    echo ""
    echo "You need your API keys. Get them from:"
    echo "  - DropLeads: your DropLeads dashboard"
    echo "  - Instantly: app.instantly.ai > Settings > API"
    echo ""
    read -p "Paste your DropLeads API key (or press Enter to skip): " DL_KEY
    read -p "Paste your Instantly API key (or press Enter to skip): " IN_KEY
    echo ""
    cat > .env << EOF
DROPLEADS_API_KEY=$DL_KEY
INSTANTLY_API_KEY=$IN_KEY
EOF
    echo "Saved to .env file."
    echo ""
fi

echo "Starting... (your browser will open automatically)"
echo ""
python3 campaign_app.py

#!/bin/bash

# TellTims Survey Automator - Raspberry Pi Deployment Script
# Run this script on your Raspberry Pi 5

echo "Starting deployment..."

# 1. Update System
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install System Dependencies
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-venv chromium-browser chromium-chromedriver tesseract-ocr libtesseract-dev libatlas-base-dev

# 3. Create Python Virtual Environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Install Python Packages
echo "Installing Python packages..."
# Note: opencv-python-headless is preferred for server/RPi environments
pip install flask selenium pytesseract pillow opencv-python-headless webdriver-manager

# 5. Install Ngrok (ARM64)
echo "Installing Ngrok..."
if ! command -v ngrok &> /dev/null; then
    wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz
    sudo tar xvzf ngrok-v3-stable-linux-arm64.tgz -C /usr/local/bin
    rm ngrok-v3-stable-linux-arm64.tgz
    echo "Ngrok installed."
else
    echo "Ngrok already installed."
fi

# 6. Create Start Script
echo "Creating start script..."
cat > start_app.sh << EOL
#!/bin/bash
cd "\$(dirname "\$0")"
source venv/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=production

# Check if port 5001 is in use and kill the process
PORT=5001
PID=\$(lsof -t -i:\$PORT)
if [ -n "\$PID" ]; then
    echo "Port \$PORT is in use by PID \$PID. Killing it..."
    kill -9 \$PID
    sleep 1
fi

# Start Flask in background
python3 app.py &
FLASK_PID=\$!

# Wait for Flask
sleep 5

# Start Ngrok
echo "Starting Ngrok..."
ngrok http 5001 > /dev/null &

echo "App running! Access via Ngrok URL."
echo "Press Ctrl+C to stop."

# Cleanup function
cleanup() {
    echo "Stopping app..."
    kill \$FLASK_PID
    pkill ngrok
    exit
}

trap cleanup SIGINT

wait \$FLASK_PID
EOL

chmod +x start_app.sh

echo "Deployment complete!"
echo "1. Run 'ngrok config add-authtoken YOUR_TOKEN' to authenticate ngrok"
echo "2. Run './start_app.sh' to start the application"

#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
export FLASK_APP=app.py
export FLASK_ENV=production

# Check if port 5001 is in use and kill the process
PORT=5001
PID=$(lsof -t -i:$PORT 2>/dev/null)
if [ -n "$PID" ]; then
    echo "Port $PORT is in use by PID $PID. Killing it..."
    kill -9 $PID
    sleep 1
fi

# Start Flask in background
python3 app.py &
FLASK_PID=$!

# Wait for Flask
sleep 3

# Start Ngrok (stop any leftover tunnel first, or ngrok refuses: endpoint already online)
pkill -f "ngrok http" 2>/dev/null && sleep 1
echo "Starting Ngrok tunnel on port 5001..."
ngrok http 5001 > /dev/null &
NGROK_PID=$!

echo "App running! Access via your Ngrok public URL."
echo "Check your Ngrok dashboard (https://dashboard.ngrok.com/endpoints/status) to find the public URL."
echo "Press Ctrl+C to stop."

# Cleanup function
cleanup() {
    echo "Stopping app..."
    kill $FLASK_PID 2>/dev/null
    kill $NGROK_PID 2>/dev/null
    pkill -f "ngrok http 5001" 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

wait $FLASK_PID

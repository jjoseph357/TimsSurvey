# Raspberry Pi 5 Deployment Guide

This guide will help you deploy the TellTims Survey Automator to your Raspberry Pi 5.

## Prerequisites

*   Raspberry Pi 5 with Raspberry Pi OS (64-bit) installed.
*   Internet connection on the Pi.
*   An Ngrok account (free) for remote access.

## Installation

1.  **Transfer Files**: Copy the project folder to your Raspberry Pi (e.g., using `scp` or a USB drive).
    *   You can clone the repo if you have git installed: `git clone https://github.com/jjoseph357/TimsSurvey.git`

2.  **Run Deployment Script**:
    Open a terminal in the project folder and run:
    ```bash
    chmod +x deploy_rpi.sh
    ./deploy_rpi.sh
    ```
    This will install all necessary dependencies (Chromium, Tesseract, Python libraries, Ngrok).

3.  **Configure Ngrok**:
    You need to add your auth token to enable the tunnel. Get it from your [Ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
    ```bash
    ngrok config add-authtoken YOUR_AUTH_TOKEN
    ```

## Running the App

To start the application:

```bash
./start_app.sh
```

The script will:
1.  Start the Flask web server on port 5001.
2.  Start an Ngrok tunnel to port 5001.
3.  Keep running in the background.

**To access the app:**
Go to your [Ngrok Dashboard > Endpoints](https://dashboard.ngrok.com/endpoints/status) to see the public URL (e.g., `https://random-name.ngrok-free.app`). Open this URL on your phone.

## Auto-Start on Boot (Optional)

To make the app start automatically when the Pi turns on:

1.  Edit the crontab:
    ```bash
    crontab -e
    ```
2.  Add this line at the end (replace `/path/to/TimsSurvey` with your actual path):
    ```bash
    @reboot /path/to/TimsSurvey/start_app.sh >> /path/to/TimsSurvey/app.log 2>&1
    ```

## Troubleshooting

*   **"Driver not found"**: The script installs `chromium-chromedriver`. If Selenium complains, ensure `survey_automator.py` is using the installed driver. The updated code should handle this automatically.
*   **Slow performance**: The Pi 5 is fast, but OCR can be CPU intensive. Ensure you have good cooling.

## Updating the App

If you need to update the app to the latest version (e.g., to get multi-user support):

1.  **Stop the running app**:
    *   If running in terminal: Press `Ctrl+C`.
    *   If running as a service: `sudo systemctl stop telltims` (if you set that up).

2.  **Pull latest changes**:
    ```bash
    cd TimsSurvey
    git pull
    ```

3.  **Restart the app**:
    ```bash
    ./start_app.sh
    ```

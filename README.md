# TellTims Survey Automator

A visually appealing GUI application to automatically navigate through the TellTims (Tim Hortons) customer survey.

## Features

- **Manual Code Entry**: Type your 21-digit survey code directly
- **Camera Capture**: Take a photo of your receipt and extract the code via OCR
- **Image Upload**: Upload a receipt image for OCR processing
- **Automated Navigation**: Uses specific element selectors for reliable automation
- **Speed Control**: Adjust navigation speed from fast to slow
- **Headless Mode**: Run browser in background
- **Validation Code Display**: Shows your reward code upon completion
- **Tim Hortons Themed UI**: Visually appealing interface with brand colors

## Installation

### Prerequisites

1. **Python 3.7+**
2. **Chrome Browser** installed
3. **ChromeDriver** (automatically managed by Selenium 4+)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### For OCR Support (Required for camera/image features)

Install Tesseract OCR:

- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

### Option 1: Local Web Interface (Recommended)

This runs the application locally on your computer with a user-friendly web interface. No internet exposure or deployment required.

1.  **Start the App**:
    ```bash
    python app.py
    ```
2.  **Open in Browser**:
    *   Open your web browser and go to: `http://localhost:5001`
3.  **Use the App**:
    *   **Manual Entry**: Click the "Manual Entry" tab and type your 21-digit code.
    *   **Upload**: Upload a photo of your receipt.
    *   **Camera**: Use your webcam to scan a receipt.

### Option 2: Remote Access (Mobile/Ngrok)

If you want to access the app from your phone while it runs on your computer:

1.  **Run the Start Script**:
    *   Double-click `start_ngrok.bat` (Windows)
    *   Or run `./start_ngrok.bat` in terminal
2.  **Scan QR / Visit URL**:
    *   The script will show a public URL (e.g., `https://xyz.ngrok-free.app`).
    *   Open this URL on your phone to use the app remotely.

### Option 3: Legacy CLI

```bash
python telltims_automator.py
```
Follow the command-line prompts to enter your code.

## Free Hosting Options

**Note: GitHub Pages will NOT work** - it only hosts static files and cannot run Python/Selenium.

### Recommended Free Hosting Platforms

#### 1. Replit (Easiest - Recommended)

**Setup Steps:**
1. Go to [replit.com](https://replit.com) and create account
2. Click "Create Repl" → Select "Python"
3. Upload your files (`telltims_automator.py`, `requirements.txt`)
4. Create a `replit.nix` file with this content:

```nix
{ pkgs }: {
  deps = [
    pkgs.python310
    pkgs.tesseract
    pkgs.chromium
    pkgs.chromedriver
  ];
}
```

5. Update `requirements.txt` to include:
```
selenium>=4.0.0
Pillow>=9.0.0
pytesseract>=0.3.10
opencv-python-headless>=4.5.0
flask>=2.0.0
```

6. For web interface, create `main.py` (see Converting to Web App section)
7. Click "Run"

**Note:** For the desktop GUI version, Replit works best with their "Desktop" template or using VNC

#### 2. Render
- [render.com](https://render.com)
- Free web service tier
- Supports Python with Chrome/Selenium
- Add to `render.yaml`:
```yaml
services:
  - type: web
    name: telltims-automator
    env: python
    buildCommand: pip install -r requirements.txt && apt-get install -y chromium-browser
    startCommand: python app.py
```

#### 3. Railway
- [railway.app](https://railway.app)
- $5 free credit monthly
- Easy GitHub deployment
- Supports background workers

#### 4. PythonAnywhere
- [pythonanywhere.com](https://pythonanywhere.com)
- Free tier available
- Note: Selenium requires paid tier for external URLs

#### 5. Google Cloud Run (Free Tier)
- 2 million requests/month free
- Requires Dockerfile with Chrome

### Converting to Web App

To host on these platforms, convert to Flask:

```python
from flask import Flask, render_template, request, jsonify
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-survey', methods=['POST'])
def run_survey():
    code = request.json['code']
    # Run automation here
    return jsonify({'status': 'complete', 'validation_code': '...'})
```

### Mobile Access

Once hosted, mobile users can:
1. Visit your hosted URL in their browser
2. Use HTML5 camera input: `<input type="file" accept="image/*" capture="camera">`
3. Submit code and view results

## Mobile App Packaging

### Option 1: Kivy (Cross-platform Mobile App)
```bash
pip install kivy buildozer
```
- Rewrite GUI using Kivy framework
- Use `buildozer` to package for Android

### Option 2: BeeWare (Native Mobile Apps)
```bash
pip install briefcase
```
- Rewrite using Toga GUI toolkit
- Package with Briefcase for iOS/Android

### Note on Mobile Limitations
- Selenium requires a desktop browser environment
- Mobile apps need server-side automation (client-server architecture)

## Survey Flow

The automation completes the following steps:
1. Enters survey code
2. Selects "Yes" for receipt question
3. Rates overall satisfaction as "Highly Satisfied"
4. Enters "Customer service" as feedback
5. Selects "Dine-In" for visit type
6. Selects "Front counter" for order method
7. Selects "Beverage only" for order type
8. Rates all service aspects as "Highly Satisfied"
9. Completes remaining questions with default positive responses
10. Displays validation code for free item reward

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with the survey's terms of service.

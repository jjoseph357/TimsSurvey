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

```bash
python telltims_automator.py
```

1. Enter your survey code manually, take a photo, or upload a receipt image
2. Adjust speed settings as needed
3. Click "Start Survey"
4. The browser will navigate through all survey questions automatically
5. Your validation code will be displayed upon completion

## Mobile Packaging Options

To run this app on mobile devices, consider these approaches:

### Option 1: Web-Based Version (Recommended for Mobile)
Convert to a Flask/Django web app that mobile users can access via browser:
- Host on a server (Heroku, AWS, etc.)
- Users access via mobile browser
- Camera capture uses HTML5 `<input type="file" capture="camera">`

### Option 2: Kivy (Cross-platform Mobile App)
```bash
pip install kivy buildozer
```
- Rewrite GUI using Kivy framework
- Use `buildozer` to package for Android
- Use `kivy-ios` for iOS builds

### Option 3: BeeWare (Native Mobile Apps)
```bash
pip install briefcase
```
- Rewrite using Toga GUI toolkit
- Package with Briefcase for iOS/Android

### Option 4: PyQt + PyQtDeploy
- Rewrite GUI in PyQt5/6
- Use pyqtdeploy for mobile packaging

### Option 5: Remote Access
- Run the desktop app on a server
- Access via remote desktop (VNC, TeamViewer)
- Or expose via web interface using PyWebIO

### Note on Mobile Limitations
- Selenium requires a desktop browser environment
- Mobile packaging typically requires:
  - A web-based approach (server runs automation, mobile is just UI)
  - Or using Appium for native mobile browser automation

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

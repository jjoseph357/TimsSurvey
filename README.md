# TellTims Survey Automator

A visually appealing GUI application to automatically navigate through the TellTims (Tim Hortons) customer survey using keyboard navigation.

## Features

- **Manual Code Entry**: Type your survey code directly
- **OCR Support**: Upload a receipt image to extract the survey code automatically
- **Keyboard Navigation**: Uses Tab and Enter to navigate (accessible automation)
- **Customizable Speed**: Adjust navigation speed from fast to slow
- **Auto-Answer Option**: Automatically select first option for each question
- **Headless Mode**: Run browser in background
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

### For OCR Support (Optional)

Install Tesseract OCR:

- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

```bash
python telltims_automator.py
```

1. Enter your survey code manually OR upload a receipt image
2. Adjust speed and settings as needed
3. Click "Start Survey"
4. The browser will open and navigate through the survey automatically

## Settings

- **Navigation Speed**: Controls delay between actions (0.1s - 2.0s)
- **Auto-select first option**: Automatically selects the first available answer
- **Headless mode**: Runs browser without visible window

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with the survey's terms of service.

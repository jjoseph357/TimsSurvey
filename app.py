#!/usr/bin/env python3
"""
TellTims Survey Automator - Web Version
Flask web application for Render deployment
"""

from flask import Flask, render_template, request, jsonify
import threading
import time
import re
import os
import base64
from io import BytesIO

# Optional imports
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

app = Flask(__name__)

# Store automation status
automation_status = {
    'running': False,
    'messages': [],
    'complete': False,
    'error': None
}

def log_status(message):
    """Log a status message"""
    timestamp = time.strftime("%H:%M:%S")
    automation_status['messages'].append(f"[{timestamp}] {message}")

def click_element_by_id(driver, element_id, timeout=15):
    """Click element by ID using JavaScript"""
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(f"return document.getElementById('{element_id}') !== null")
    )
    driver.execute_script(f"""
        var element = document.getElementById('{element_id}');
        if (element) {{
            element.scrollIntoView(true);
            element.click();
        }}
    """)
    time.sleep(0.3)

def wait_and_click(driver, by, value, timeout=15):
    """Wait for element and click it"""
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, value)))
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
    driver.execute_script("arguments[0].scrollIntoView(true);", element)
    time.sleep(0.3)
    element.click()
    return element

def wait_for_element(driver, by, value, timeout=15):
    """Wait for element to be present"""
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, value)))

def wait_for_page_load(driver):
    """Wait for page to load"""
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(0.5)

def click_next(driver, delay=0.3):
    """Click Next button"""
    wait_and_click(driver, By.ID, "NextButton")
    time.sleep(delay)
    wait_for_page_load(driver)

def run_survey_automation(survey_code):
    """Run the survey automation"""
    global automation_status
    automation_status['running'] = True
    automation_status['messages'] = []
    automation_status['complete'] = False
    automation_status['error'] = None

    driver = None
    delay = 0.3

    try:
        log_status("Initializing browser...")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # For Render deployment
        options.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium-browser')

        driver = webdriver.Chrome(options=options)

        log_status("Opening TellTims survey...")
        driver.get("https://telltims.ca/")
        time.sleep(3)

        # Switch to iframe
        try:
            iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "iframe"))
            )
            driver.switch_to.frame(iframe)
            log_status("Switched to survey iframe")
        except:
            log_status("No iframe found")

        time.sleep(2)

        # Page 1: Enter survey code
        log_status(f"Entering survey code: {survey_code}")
        wait_for_page_load(driver)
        code_input = wait_for_element(driver, By.ID, "QR~QID9")
        code_input.clear()
        code_input.send_keys(survey_code)
        click_next(driver, delay)
        log_status("Code submitted")

        # Page 2: Click Yes
        log_status("Selecting 'Yes'...")
        wait_for_page_load(driver)
        click_element_by_id(driver, "QR~QID14~1")
        click_next(driver, delay)

        # Page 3: Highly Satisfied
        log_status("Selecting 'Highly Satisfied'...")
        click_element_by_id(driver, "QR~QID15~4")
        click_next(driver, delay)

        # Page 4: Enter text
        log_status("Entering feedback text...")
        wait_for_page_load(driver)
        textarea = wait_for_element(driver, By.ID, "QR~QID45")
        textarea.clear()
        textarea.send_keys("Customer service")
        click_next(driver, delay)

        # Page 5: Dine-In
        log_status("Selecting 'Dine-In'...")
        click_element_by_id(driver, "QR~QID18~5")
        click_next(driver, delay)

        # Page 6: Front counter
        log_status("Selecting 'Front counter'...")
        click_element_by_id(driver, "QR~QID19~5")
        click_next(driver, delay)

        # Page 7: Beverage only
        log_status("Selecting 'Beverage only'...")
        click_element_by_id(driver, "QR~QID20~5")
        click_next(driver, delay)

        # Page 8: Satisfaction ratings
        log_status("Rating all items 'Highly Satisfied'...")
        satisfaction_ids = [
            "QR~QID23~4~1", "QR~QID23~6~1", "QR~QID23~7~1",
            "QR~QID23~8~1", "QR~QID23~10~1", "QR~QID23~11~1"
        ]
        for radio_id in satisfaction_ids:
            try:
                click_element_by_id(driver, radio_id)
                time.sleep(delay * 0.2)
            except Exception as e:
                log_status(f"Could not find {radio_id}")
        click_next(driver, delay)

        # Page 9: Empty page
        log_status("Proceeding...")
        click_next(driver, delay)

        # Page 10: No
        log_status("Selecting 'No'...")
        click_element_by_id(driver, "QR~QID151~3")
        click_next(driver, delay)

        # Page 11: Highly Likely
        log_status("Selecting 'Highly Likely'...")
        click_element_by_id(driver, "QR~QID44~1~1")
        time.sleep(delay * 0.3)
        click_element_by_id(driver, "QR~QID44~3~1")
        click_next(driver, delay)

        # Page 12: No
        log_status("Selecting 'No'...")
        click_element_by_id(driver, "QR~QID37~2")
        click_next(driver, delay)

        # Page 13: No
        log_status("Selecting 'No'...")
        click_element_by_id(driver, "QR~QID134~2")
        click_next(driver, delay)

        # Page 14: Yes
        log_status("Selecting 'Yes'...")
        click_element_by_id(driver, "QR~QID150~2")
        click_next(driver, delay)

        # Page 15: Something else
        log_status("Selecting 'Something else'...")
        click_element_by_id(driver, "QR~QID48~5")
        click_next(driver, delay)

        # Page 16: No
        log_status("Selecting 'No'...")
        click_element_by_id(driver, "QR~QID68~2")
        click_next(driver, delay)

        # Extract validation code
        log_status("Survey complete! Extracting validation code...")
        time.sleep(1)

        page_source = driver.page_source
        # Look for validation code pattern like "CB38847"
        match = re.search(r'Validation Code[:\s]*([A-Z0-9]+)', page_source, re.IGNORECASE)
        if match:
            validation_code = match.group(1)
            log_status(f"VALIDATION CODE: {validation_code}")
        else:
            log_status("Survey completed! Check page for validation code.")

        automation_status['complete'] = True
        log_status("Automation completed successfully!")

    except TimeoutException as e:
        log_status(f"Timeout: {str(e)}")
        automation_status['error'] = str(e)
    except Exception as e:
        log_status(f"Error: {str(e)}")
        automation_status['error'] = str(e)
    finally:
        if driver:
            driver.quit()
        automation_status['running'] = False

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', ocr_available=OCR_AVAILABLE)

@app.route('/run-survey', methods=['POST'])
def run_survey():
    """Start survey automation"""
    if not SELENIUM_AVAILABLE:
        return jsonify({'error': 'Selenium not available'}), 500

    data = request.json
    survey_code = data.get('code', '').strip()

    if not survey_code:
        return jsonify({'error': 'Survey code required'}), 400

    if automation_status['running']:
        return jsonify({'error': 'Automation already running'}), 400

    # Run in background thread
    thread = threading.Thread(target=run_survey_automation, args=(survey_code,))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})

@app.route('/status')
def get_status():
    """Get automation status"""
    return jsonify(automation_status)

@app.route('/extract-code', methods=['POST'])
def extract_code():
    """Extract survey code from uploaded image"""
    if not OCR_AVAILABLE:
        return jsonify({'error': 'OCR not available. Install pytesseract.'}), 500

    if 'image' not in request.files and 'image_data' not in request.json:
        return jsonify({'error': 'No image provided'}), 400

    try:
        if 'image' in request.files:
            # File upload
            file = request.files['image']
            image = Image.open(file.stream)
        else:
            # Base64 image data
            image_data = request.json['image_data']
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image = Image.open(BytesIO(base64.b64decode(image_data)))

        # Perform OCR
        text = pytesseract.image_to_string(image)

        # Find survey code patterns
        patterns = [
            r'\b\d{21}\b',
            r'\b\d{18,24}\b',
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            r'\b\d{12,16}\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                code = matches[0].replace('-', '').replace(' ', '')
                return jsonify({'code': code})

        return jsonify({'error': 'Could not find survey code in image'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

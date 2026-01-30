import os
import time
import threading
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Camera/OCR dependencies have been removed per request

class DriverPool:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_drivers=3):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DriverPool, cls).__new__(cls)
                cls._instance.max_drivers = max_drivers
                cls._instance.drivers = []  # List of {'driver': driver, 'busy': bool}
                cls._instance.pool_lock = threading.Lock()
        return cls._instance

    def get_driver(self):
        with self.pool_lock:
            # 1. Try to find an idle driver
            for i, item in enumerate(self.drivers):
                if not item['busy']:
                    try:
                        # Check if alive
                        item['driver'].title
                        item['busy'] = True
                        logger.info(f"Reusing existing driver {i}")
                        return item['driver']
                    except Exception as e:
                        logger.warning(f"Found dead driver in pool, removing: {e}")
                        try:
                            item['driver'].quit()
                        except:
                            pass
                        self.drivers.pop(i)
            
            # 2. If no idle driver, create new if under limit
            if len(self.drivers) < self.max_drivers:
                logger.info(f"Creating new driver ({len(self.drivers) + 1}/{self.max_drivers})")
                driver = self._create_driver()
                self.drivers.append({'driver': driver, 'busy': True})
                return driver
            
            # 3. If full, return None (caller should handle busy state)
            logger.warning("Driver pool exhausted!")
            return None

    def release_driver(self, driver):
        with self.pool_lock:
            for item in self.drivers:
                if item['driver'] == driver:
                    try:
                        # Reset state for next user
                        driver.delete_all_cookies()
                        driver.get("about:blank")
                        item['busy'] = False
                        logger.info("Driver released back to pool")
                    except Exception as e:
                        logger.error(f"Error releasing driver: {e}")
                        # If we can't reset it, kill it
                        try:
                            driver.quit()
                        except:
                            pass
                        self.drivers.remove(item)
                    return

    def _create_driver(self):
        options = Options()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--window-size=1920,1080')
        # Stealth settings
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # RPi/Linux specific: Check for system chromedriver
        import platform
        if platform.system() == 'Linux':
            options.add_argument('--headless=new') # Optional: Run headless on Pi
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Try using system chromedriver first (common on RPi)
            system_driver_path = "/usr/bin/chromedriver"
            if os.path.exists(system_driver_path):
                service = Service(system_driver_path)
            else:
                try:
                    service = Service(ChromeDriverManager().install())
                except:
                    # Fallback for RPi if manager fails
                    service = Service("/usr/lib/chromium-browser/chromedriver")
        else:
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)
        
        # Stealth JS
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver

# Global accessor
def get_driver_pool():
    return DriverPool()

class SurveyAutomator:
    def __init__(self):
        self.driver = None
        self.status = "Idle"
        self.progress = 0
        self.logs = []
        self.result_code = None
        self.result_image_path = None
        self.is_running = False

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        self.status = message
        logger.info(message)

    def extract_code_from_text(self, text):
        # Method 1: Regex patterns
        patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{5}\b',
            r'\b\d{21}\b',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                clean_code = matches[0].replace('-', '').replace(' ', '')
                if len(clean_code) == 21:
                    return clean_code
        
        # Method 2: Brute Force
        digits_only = re.sub(r'\D', '', text)
        match = re.search(r'\d{21}', digits_only)
        if match:
            return match.group(0)
        return None

    # Camera scanning features removed

    def find_input_in_context(self):
        """Try to find the survey code input field"""
        selectors = [
            (By.ID, "CN1"), (By.NAME, "CN1"), (By.CSS_SELECTOR, "input[name='CN1']"),
            (By.CSS_SELECTOR, "input[id='CN1']"), (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[type='tel']"), (By.CSS_SELECTOR, "input[type='number']"),
            (By.XPATH, "//input[contains(@id, 'CN')]"), (By.XPATH, "//input[contains(@name, 'CN')]")
        ]
        for by, value in selectors:
            try:
                elements = self.driver.find_elements(by, value)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        return el
            except: continue
        return None

    def click_element_js(self, element_id):
        """Robust JavaScript click with improved waiting for RPi5"""
        self.log(f"Clicking {element_id}...")
        try:
            # 1. Wait for presence
            WebDriverWait(self.driver, 40).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            
            # 2. Direct Force Click (Optimization: Skip clickable check)
            # User reported standard check times out, so we go straight to JS click
            pass

            # 3. JS Click with retry
            max_retries = 3
            for i in range(max_retries):
                try:
                    self.driver.execute_script(f"""
                        var el = document.getElementById('{element_id}');
                        if(el) {{
                            el.scrollIntoView({{behavior: 'auto', block: 'center'}});
                            el.click();
                        }} else {{
                            throw new Error('Element not found: {element_id}');
                        }}
                    """)
                    time.sleep(1.0) # Increased dwell time for RPi
                    return
                except Exception as retry_err:
                    if i == max_retries - 1: raise retry_err
                    time.sleep(1)
                    
        except Exception as e:
            self.log(f"Error clicking {element_id}: {e}")
            raise

    def click_next(self):
        """Click NextButton with retry logic"""
        self.log("Clicking Next...")
        # time.sleep(1) # Removed initial delay
        
        max_retries = 3
        for i in range(max_retries):
            try:
                # Check if button exists
                exists = self.driver.execute_script("return document.getElementById('NextButton') !== null")
                if not exists:
                    self.log("NextButton not found in DOM")
                    time.sleep(1)
                    continue

                # Click
                self.driver.execute_script("""
                    var btn = document.getElementById('NextButton');
                    btn.scrollIntoView({behavior: 'auto', block: 'center'});
                    btn.click();
                """)
                
                # Wait for page load/transition
                time.sleep(0.5)
                
                # Verify navigation (simple check: did URL change or element disappear?)
                # For now, just assuming success if no error, but we can be smarter
                return
            except Exception as e:
                self.log(f"Retry {i+1} failed: {e}")
                time.sleep(2)
        
        raise Exception("Failed to click NextButton after retries")

    def wait_for_page_load(self):
        try:
            WebDriverWait(self.driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(0.2)
        except:
            pass
    def complete_survey_pages(self):
        # NOTE: Exception handling is done in start_survey to capture debug info
        
        # Iframe Safeguard: Ensure we are still in the iframe (Page transitions can lose context)
        try:
            if not self.driver.find_elements(By.ID, "QR~QID14~1"):
                 # Try finding iframe again
                 frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                 if frames:
                     self.driver.switch_to.default_content()
                     self.driver.switch_to.frame(frames[0])
                     self.log("Re-switched to iframe for Page 2")
        except: pass

        
        # Page 2: Yes
        self.wait_for_page_load()
        
        # DEBUG: Dump Page 2 HTML to see what's wrong with QID14
        try:
            import tempfile
            fname = f"page2_debug_{int(time.time())}.html"
            fpath = os.path.join(tempfile.gettempdir(), fname)
            with open(fpath, "w", encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self.log(f"DUMPED PAGE 2 HTML to {fpath} - Checking for QID14")
        except: pass

        # DEBUG: Check if we actually moved
        try:
            if self.driver.find_elements(By.ID, "QR~QID9"):
                self.log("STUCK ON PAGE 1: Input field still visible. Code might be invalid.")
                # Check for error message
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "Error" in body_text or "Invalid" in body_text or "check the code" in body_text:
                    raise Exception("Survey rejected the code (Invalid/Used).")
                raise Exception("Failed to navigate from Start Page")
        except Exception as nav_err:
            if "Survey rejected" in str(nav_err): raise nav_err
            # If finding the element failed, we might have moved? Continue.
        
        self.click_element_js("QR~QID14~1")
        self.click_next()
        self.progress = 50

        # Page 3: Highly Satisfied
        self.wait_for_page_load()
        self.click_element_js("QR~QID15~4")
        self.click_next()
        self.progress = 55

        # Page 4: Feedback
        self.wait_for_page_load()
        try:
            textarea = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "QR~QID45"))
            )
            textarea.clear()
            textarea.send_keys("Great service")
        except:
            self.log("Feedback area not found, skipping")
        self.click_next()
        self.progress = 60

        # Page 5: Dine-In
        self.wait_for_page_load()
        self.click_element_js("QR~QID18~5")
        self.click_next()
        self.progress = 65

        # Page 6: Front counter
        self.wait_for_page_load()
        self.click_element_js("QR~QID19~5")
        self.click_next()
        self.progress = 70

        # Page 7: Beverage only
        self.wait_for_page_load()
        self.click_element_js("QR~QID20~5")
        self.click_next()
        self.progress = 72

        # Page 8: Matrix (Highly Satisfied)
        self.wait_for_page_load()
        ids = ["QR~QID23~4~1", "QR~QID23~6~1", "QR~QID23~7~1", 
                "QR~QID23~8~1", "QR~QID23~10~1", "QR~QID23~11~1"]
        for eid in ids:
            try:
                self.click_element_js(eid)
            except:
                pass # Optional rows
        self.click_next()
        self.progress = 75

        # Page 9: Empty/Next
        self.wait_for_page_load()
        self.click_next()
        self.progress = 78

        # Page 10: No
        self.wait_for_page_load()
        self.click_element_js("QR~QID151~3")
        self.click_next()
        self.progress = 80

        # Page 11: Highly Likely x2
        self.wait_for_page_load()
        self.click_element_js("QR~QID44~1~1")
        self.click_element_js("QR~QID44~3~1")
        self.click_next()
        self.progress = 83

        # Page 12: No
        self.wait_for_page_load()
        self.click_element_js("QR~QID37~2")
        self.click_next()
        self.progress = 85

        # Page 13: No
        self.wait_for_page_load()
        self.click_element_js("QR~QID134~2")
        self.click_next()
        self.progress = 87

        # Page 14: Yes
        self.wait_for_page_load()
        self.click_element_js("QR~QID150~2")
        self.click_next()
        self.progress = 90

        # Page 15: Something else
        self.wait_for_page_load()
        self.click_element_js("QR~QID48~5")
        self.click_next()
        self.progress = 93

        # Page 16: No
        self.wait_for_page_load()
        self.click_element_js("QR~QID68~2")
        self.click_next()
        self.progress = 95

        return True

    def extract_validation_code(self):
        try:
            time.sleep(2)
            text = self.driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r'Validation Code:?\s*(\d+)', text, re.IGNORECASE)
            if match: return match.group(1)
            match = re.search(r'\b\d{7}\b', text)
            if match: return match.group(0)
        except:
            pass
        return None

    def start_survey(self, code, on_success=None):
        self.is_running = True
        self.progress = 0
        self.logs = []
        self.result_code = None
        self.result_image_path = None
        
        pool = get_driver_pool()
        self.driver = pool.get_driver()
        
        if not self.driver:
            self.log("System busy: No browsers available")
            self.is_running = False
            return

        try:
            self.log(f"Starting survey for code: {code}")
            self.driver.get("https://www.telltims.ca/")
            self.progress = 10
            
            # Wait for body
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(0.5)

            # Iframe check
            try:
                iframe = self.driver.find_element(By.TAG_NAME, "iframe")
                self.driver.switch_to.frame(iframe)
                self.log("Switched to iframe")
            except:
                self.log("No iframe found")

            # Input Code
            self.log("Entering code...")
            try:
                input_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "QR~QID9"))
                )
            except:
                input_field = self.find_input_in_context()
            
            if not input_field:
                raise Exception("Input field not found")

            input_field.clear()
            
            # 1. Human-like Typing (Triggers 'input' events)
            self.log("Typing code...")
            for char in code:
                input_field.send_keys(char)
                time.sleep(0.05) # fast but distinct typing
            
            # 2. Force Blur (Click Body) - Triggers validation
            try:
                self.driver.execute_script("arguments[0].blur();", input_field)
                self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            
            time.sleep(1) # Wait for "Disabled" attribute to be removed
            
            # Try ENTER key first (standard form submission)
            self.log("Sending ENTER key...")
            input_field.send_keys(Keys.ENTER)
            time.sleep(2)

            # Check if we moved (Input field should be gone)
            try:
                if self.driver.find_elements(By.ID, "QR~QID9"):
                    self.log("ENTER key didn't work, trying Click Next...")
                    self.click_next()
                    # Wait for transition
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, "QR~QID9"))
                    )
            except Exception as e:
                self.log(f"Transition warning: {e}")
            
            self.progress = 40

            # Run pages
            if self.complete_survey_pages():
                self.log("Survey pages completed")
                self.progress = 98
                
                # Validation Code
                code = self.extract_validation_code()
                if code:
                    self.result_code = code
                    self.log(f"Validation Code: {code}")
                
                # Screenshot
                import tempfile
                fname = f"result_{int(time.time())}.png"
                fpath = os.path.join(tempfile.gettempdir(), fname)
                self.driver.save_screenshot(fpath)
                self.result_image_path = fpath
                self.progress = 100
                self.status = "Completed"
                if on_success:
                    try:
                        on_success()
                    except Exception as cb_err:
                        self.log(f"Callback error: {cb_err}")
            else:
                self.status = "Failed during pages"

        except Exception as e:
            self.log(f"Critical Error: {e}")
            self.status = "Error"
            
            # Enhanced Debugging
            try:
                if self.driver:
                    self.log(f"Current URL: {self.driver.current_url}")
                    self.log(f"Page Title: {self.driver.title}")
                    
                    import tempfile
                    # Screenshot
                    fname_img = f"error_{int(time.time())}.png"
                    fpath_img = os.path.join(tempfile.gettempdir(), fname_img)
                    self.driver.save_screenshot(fpath_img)
                    self.result_image_path = fpath_img 
                    
                    # HTML Dump
                    fname_html = f"error_{int(time.time())}.html"
                    fpath_html = os.path.join(tempfile.gettempdir(), fname_html)
                    with open(fpath_html, "w", encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.log(f"Saved debug HTML to {fpath_html}")
            except Exception as debug_err:
                self.log(f"Failed to save debug info: {debug_err}")
            
            
        finally:
            self.is_running = False
            # CRITICAL: Release driver, don't close it
            if self.driver:
                pool.release_driver(self.driver)
                self.driver = None

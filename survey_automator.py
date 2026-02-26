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
        system_os = platform.system()
        
        if system_os == 'Linux':
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
        
        else: # Windows / Mac
            # Windows: Explicitly look for Chrome binary if not found in PATH
            if system_os == 'Windows':
                possible_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ]
                
                # Try Registry
                try:
                    import winreg
                    reg_paths = [
                        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
                        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                    ]
                    for root, key_path in reg_paths:
                        try:
                            with winreg.OpenKey(root, key_path) as key:
                                path, _ = winreg.QueryValueEx(key, "")
                                if path: possible_paths.append(path)
                        except: pass
                except ImportError: pass

                binary_found = False
                for p in possible_paths:
                    if os.path.exists(p):
                        logger.info(f"Found Chrome binary at: {p}")
                        options.binary_location = p
                        binary_found = True
                        break
                
                if not binary_found:
                    logger.error("CRITICAL: Google Chrome binary NOT found in Registry or standard paths.")
                    logger.error("Please install Google Chrome from https://www.google.com/chrome/")
                    logger.error("If installed, please add 'chrome.exe' to your System PATH.")
                    # Let it fail naturally if we can't find it, but the log helps.

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

    def wait_for_next_page(self, element_id, timeout=10):
        """Poll every 100ms until the expected element appears on the next page."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                el = self.driver.find_element(By.ID, element_id)
                if el.is_displayed():
                    return True
            except:
                pass
            time.sleep(0.1)
        # Fallback: just check readyState
        try:
            WebDriverWait(self.driver, 3).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            pass
        return False

    def click_and_next(self, element_id):
        """Click an element AND NextButton in a single JS execution — minimizes Selenium round-trips."""
        self.log(f"Clicking {element_id} + Next...")
        max_retries = 3
        for i in range(max_retries):
            try:
                self.driver.execute_script(f"""
                    var el = document.getElementById('{element_id}');
                    if(el) {{ el.scrollIntoView({{behavior: 'auto', block: 'center'}}); el.click(); }}
                    var btn = document.getElementById('NextButton');
                    if(btn) {{ btn.click(); }}
                """)
                return
            except Exception as retry_err:
                if i == max_retries - 1: raise retry_err
                time.sleep(0.3)

    def click_next(self):
        """Click NextButton only — for pages where element interaction is separate."""
        self.log("Clicking Next...")
        max_retries = 3
        for i in range(max_retries):
            try:
                self.driver.execute_script("""
                    var btn = document.getElementById('NextButton');
                    if(btn) { btn.scrollIntoView({behavior: 'auto', block: 'center'}); btn.click(); }
                """)
                return
            except Exception as e:
                if i == max_retries - 1: raise e
                time.sleep(0.3)

    def click_all_and_next(self, element_ids):
        """Click multiple elements AND NextButton in a single JS execution."""
        self.log(f"Batch clicking {len(element_ids)} elements + Next...")
        ids_js = ','.join(f"'{eid}'" for eid in element_ids)
        self.driver.execute_script(f"""
            var ids = [{ids_js}];
            ids.forEach(function(id) {{
                var el = document.getElementById(id);
                if(el) {{ el.scrollIntoView({{behavior: 'auto', block: 'center'}}); el.click(); }}
            }});
            var btn = document.getElementById('NextButton');
            if(btn) {{ btn.click(); }}
        """)

    def wait_for_element_gone(self, element_id, timeout=10):
        """Poll until an element disappears — used to detect page transitions."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if not self.driver.find_elements(By.ID, element_id):
                    return True
            except:
                return True
            time.sleep(0.1)
        return False

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
        self.wait_for_next_page("QR~QID14~1")
        
        # FAIL FAST: Check for error message on page 2
        try:
            body = self.driver.find_element(By.TAG_NAME, "body").text
            if "Error" in body or "Invalid" in body or "System Error" in body:
                self.log(f"Detected Error on Page: {body[:100]}")
                return False
        except: pass

        self.click_and_next("QR~QID14~1")
        self.progress = 50

        # Page 3: Highly Satisfied
        self.wait_for_next_page("QR~QID15~4")
        self.click_and_next("QR~QID15~4")
        self.progress = 55

        # Page 4: Feedback
        self.wait_for_next_page("QR~QID45")
        try:
            self.driver.execute_script("""
                var ta = document.getElementById('QR~QID45');
                if(ta) { ta.value = 'Great service'; ta.dispatchEvent(new Event('input', {bubbles:true})); }
                var btn = document.getElementById('NextButton');
                if(btn) { btn.click(); }
            """)
        except:
            self.log("Feedback page error, clicking Next anyway")
            self.click_next()
        self.progress = 60

        # Page 5: Dine-In
        self.wait_for_next_page("QR~QID18~5")
        self.click_and_next("QR~QID18~5")
        self.progress = 65

        # Page 6: Front counter
        self.wait_for_next_page("QR~QID19~5")
        self.click_and_next("QR~QID19~5")
        self.progress = 70

        # Page 7: Beverage only
        self.wait_for_next_page("QR~QID20~5")
        self.click_and_next("QR~QID20~5")
        self.progress = 72

        # Page 8: Matrix (Highly Satisfied) — batch click all 6 + Next in one JS call
        self.wait_for_next_page("QR~QID23~4~1")
        self.click_all_and_next([
            "QR~QID23~4~1", "QR~QID23~6~1", "QR~QID23~7~1",
            "QR~QID23~8~1", "QR~QID23~10~1", "QR~QID23~11~1"
        ])
        self.progress = 75

        # Page 9: Empty/Next — wait for Page 8 matrix elements to disappear
        self.wait_for_element_gone("QR~QID23~4~1")
        self.click_next()
        self.progress = 78

        # Page 10: No
        self.wait_for_next_page("QR~QID151~3")
        self.click_and_next("QR~QID151~3")
        self.progress = 80

        # Page 11: Highly Likely x2 — click both + Next in one JS call
        self.wait_for_next_page("QR~QID44~1~1")
        self.click_all_and_next(["QR~QID44~1~1", "QR~QID44~3~1"])
        self.progress = 83

        # Page 12: No
        self.wait_for_next_page("QR~QID37~2")
        self.click_and_next("QR~QID37~2")
        self.progress = 85

        # Page 13: No
        self.wait_for_next_page("QR~QID134~2")
        self.click_and_next("QR~QID134~2")
        self.progress = 87

        # Page 14: Yes
        self.wait_for_next_page("QR~QID150~2")
        self.click_and_next("QR~QID150~2")
        self.progress = 90

        # Page 15: Something else
        self.wait_for_next_page("QR~QID48~5")
        self.click_and_next("QR~QID48~5")
        self.progress = 93

        # Page 16: No
        self.wait_for_next_page("QR~QID68~2")
        self.click_and_next("QR~QID68~2")
        self.progress = 95

        return True

    def extract_validation_code(self):
        """Poll for validation code every 200ms, up to 5s."""
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                text = self.driver.find_element(By.TAG_NAME, "body").text
                match = re.search(r'Validation Code:?\s*(\d+)', text, re.IGNORECASE)
                if match: return match.group(1)
                match = re.search(r'\b\d{7}\b', text)
                if match: return match.group(0)
            except:
                pass
            time.sleep(0.2)
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
            
            # 1. Fast JS code entry with event dispatch
            self.log("Entering code via JS...")
            try:
                self.driver.execute_script("""
                    var el = arguments[0];
                    var code = arguments[1];
                    el.focus();
                    el.value = code;
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.blur();
                """, input_field, code)
            except:
                # Fallback: char-by-char typing
                self.log("JS entry failed, falling back to typing...")
                for char in code:
                    input_field.send_keys(char)
                    time.sleep(0.02)
                try:
                    self.driver.execute_script("arguments[0].blur();", input_field)
                except: pass
            
            # 2. Force Blur (Click Body) - Triggers validation
            try:
                self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            
            time.sleep(0.2) 
            
            # Retry Loop: Keep hitting Next until we actually verify we moved
            self.log("Transition Loop: Pressing Next until Page 2 appears...")
            max_attempts = 5
            transitioned = False
            
            for attempt in range(max_attempts):
                # 1. Click Next
                try:
                    self.click_next()
                except: pass 
                
                # POLL for page load (Checking every 200ms up to 2s)
                for _ in range(10):
                    time.sleep(0.2)
                    try:
                        if self.driver.find_elements(By.ID, "QR~QID14~1"):
                            self.log("Transition Verified: Found Page 2 ID")
                            transitioned = True
                            break
                        
                        body_text = self.driver.find_element(By.TAG_NAME, "body").text
                        
                        if "Is your feedback related to" in body_text:
                            self.log("Transition Verified: Found Page 2 Text")
                            transitioned = True
                            break
                    except: pass
                
                if transitioned:
                    break
                
                # Check for error messages on Page 1
                try:
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "Error" in body_text or "Invalid" in body_text:
                        raise Exception("Survey rejected the code (Invalid/Used).")
                except NameError: pass
                except Exception as e:
                    if "rejected" in str(e): raise
                    
                self.log(f"Still on Page 1 (Attempt {attempt+1}/{max_attempts})...")
                
                # Re-do validation trigger (Tab/Blur) to ensure button enables
                try:
                    input_field.send_keys(Keys.TAB)
                    self.driver.execute_script("arguments[0].blur();", input_field)
                except: pass

            if not transitioned:
                 raise Exception("Failed to verify transition to Page 2 after multiple attempts")
            
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

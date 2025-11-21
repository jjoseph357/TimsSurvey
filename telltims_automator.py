#!/usr/bin/env python3
"""
TellTims Survey Automator
A visually appealing GUI application to automatically navigate through the TellTims survey.
Supports manual code entry and OCR from images.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import re
import os

# Optional imports with graceful fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class ModernButton(tk.Canvas):
    """Custom modern-looking button with hover effects"""

    def __init__(self, parent, text, command=None, width=200, height=45,
                 bg_color="#c8102e", hover_color="#a00d24", text_color="white", **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, bg=parent.cget('bg'), **kwargs)

        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.width = width
        self.height = height
        self.text = text

        self.draw_button(self.bg_color)

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def draw_button(self, color):
        self.delete("all")
        # Draw rounded rectangle
        radius = 10
        self.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill=color, outline=color)
        self.create_arc(self.width-radius*2, 0, self.width, radius*2, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, self.height-radius*2, radius*2, self.height, start=180, extent=90, fill=color, outline=color)
        self.create_arc(self.width-radius*2, self.height-radius*2, self.width, self.height, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(radius, 0, self.width-radius, self.height, fill=color, outline=color)
        self.create_rectangle(0, radius, self.width, self.height-radius, fill=color, outline=color)
        # Draw text
        self.create_text(self.width//2, self.height//2, text=self.text,
                        fill=self.text_color, font=("Helvetica", 12, "bold"))

    def on_enter(self, event):
        self.draw_button(self.hover_color)

    def on_leave(self, event):
        self.draw_button(self.bg_color)

    def on_click(self, event):
        if self.command:
            self.command()


class TellTimsAutomator:
    """Main application class for TellTims Survey Automator"""

    def __init__(self, root):
        self.root = root
        self.root.title("TellTims Survey Automator")
        self.root.geometry("600x700")
        self.root.resizable(False, False)

        # Colors - Tim Hortons theme
        self.bg_color = "#f5f5f5"
        self.primary_color = "#c8102e"  # Tim Hortons red
        self.secondary_color = "#4a2c2a"  # Dark brown
        self.accent_color = "#ffffff"

        self.root.configure(bg=self.bg_color)

        self.driver = None
        self.is_running = False

        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI components"""

        # Header
        header_frame = tk.Frame(self.root, bg=self.primary_color, height=100)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="TellTims Survey Automator",
            font=("Helvetica", 24, "bold"),
            fg="white",
            bg=self.primary_color
        )
        title_label.pack(pady=30)

        # Main content frame
        content_frame = tk.Frame(self.root, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)

        # Survey code section
        code_section = tk.LabelFrame(
            content_frame,
            text=" Survey Code ",
            font=("Helvetica", 12, "bold"),
            fg=self.secondary_color,
            bg=self.bg_color,
            padx=20,
            pady=15
        )
        code_section.pack(fill=tk.X, pady=(0, 20))

        # Code entry
        code_label = tk.Label(
            code_section,
            text="Enter your survey code:",
            font=("Helvetica", 10),
            fg=self.secondary_color,
            bg=self.bg_color
        )
        code_label.pack(anchor=tk.W)

        self.code_entry = tk.Entry(
            code_section,
            font=("Helvetica", 14),
            justify=tk.CENTER,
            width=30
        )
        self.code_entry.pack(pady=10, ipady=8)

        # OR separator
        or_label = tk.Label(
            code_section,
            text="— OR —",
            font=("Helvetica", 10),
            fg="#888888",
            bg=self.bg_color
        )
        or_label.pack(pady=5)

        # Image upload button
        upload_btn = ModernButton(
            code_section,
            text="Upload Receipt Image",
            command=self.upload_image,
            bg_color="#4a2c2a",
            hover_color="#3a1c1a",
            width=250
        )
        upload_btn.pack(pady=10)

        # OCR status
        if not OCR_AVAILABLE:
            ocr_warning = tk.Label(
                code_section,
                text="(OCR not available - install pytesseract)",
                font=("Helvetica", 8),
                fg="#ff6b6b",
                bg=self.bg_color
            )
            ocr_warning.pack()

        # Settings section
        settings_section = tk.LabelFrame(
            content_frame,
            text=" Automation Settings ",
            font=("Helvetica", 12, "bold"),
            fg=self.secondary_color,
            bg=self.bg_color,
            padx=20,
            pady=15
        )
        settings_section.pack(fill=tk.X, pady=(0, 20))

        # Speed slider
        speed_label = tk.Label(
            settings_section,
            text="Navigation Speed:",
            font=("Helvetica", 10),
            fg=self.secondary_color,
            bg=self.bg_color
        )
        speed_label.pack(anchor=tk.W)

        speed_frame = tk.Frame(settings_section, bg=self.bg_color)
        speed_frame.pack(fill=tk.X, pady=5)

        tk.Label(speed_frame, text="Fast", font=("Helvetica", 8),
                bg=self.bg_color, fg="#888").pack(side=tk.LEFT)

        self.speed_var = tk.DoubleVar(value=0.5)
        speed_slider = ttk.Scale(
            speed_frame,
            from_=0.1,
            to=2.0,
            variable=self.speed_var,
            orient=tk.HORIZONTAL
        )
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        tk.Label(speed_frame, text="Slow", font=("Helvetica", 8),
                bg=self.bg_color, fg="#888").pack(side=tk.LEFT)

        # Auto-answer option
        self.auto_answer_var = tk.BooleanVar(value=True)
        auto_check = tk.Checkbutton(
            settings_section,
            text="Auto-select first option for each question",
            variable=self.auto_answer_var,
            font=("Helvetica", 10),
            bg=self.bg_color,
            fg=self.secondary_color,
            activebackground=self.bg_color
        )
        auto_check.pack(anchor=tk.W, pady=5)

        # Headless mode option
        self.headless_var = tk.BooleanVar(value=False)
        headless_check = tk.Checkbutton(
            settings_section,
            text="Run in background (headless mode)",
            variable=self.headless_var,
            font=("Helvetica", 10),
            bg=self.bg_color,
            fg=self.secondary_color,
            activebackground=self.bg_color
        )
        headless_check.pack(anchor=tk.W)

        # Control buttons
        button_frame = tk.Frame(content_frame, bg=self.bg_color)
        button_frame.pack(pady=20)

        start_btn = ModernButton(
            button_frame,
            text="Start Survey",
            command=self.start_survey,
            width=200
        )
        start_btn.pack(side=tk.LEFT, padx=10)

        stop_btn = ModernButton(
            button_frame,
            text="Stop",
            command=self.stop_survey,
            bg_color="#666666",
            hover_color="#444444",
            width=100
        )
        stop_btn.pack(side=tk.LEFT, padx=10)

        # Status section
        status_section = tk.LabelFrame(
            content_frame,
            text=" Status ",
            font=("Helvetica", 12, "bold"),
            fg=self.secondary_color,
            bg=self.bg_color,
            padx=20,
            pady=15
        )
        status_section.pack(fill=tk.BOTH, expand=True)

        self.status_text = tk.Text(
            status_section,
            height=8,
            font=("Courier", 9),
            bg="#ffffff",
            fg=self.secondary_color,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)

        # Scrollbar for status
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)

        # Footer
        footer_label = tk.Label(
            self.root,
            text="Use responsibly. This tool is for educational purposes only.",
            font=("Helvetica", 8),
            fg="#888888",
            bg=self.bg_color
        )
        footer_label.pack(pady=10)

        self.log_status("Ready. Enter survey code or upload image to begin.")

    def log_status(self, message):
        """Log a message to the status text area"""
        self.status_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()

    def upload_image(self):
        """Handle image upload for OCR"""
        if not OCR_AVAILABLE:
            messagebox.showerror(
                "OCR Not Available",
                "Please install pytesseract and Tesseract OCR:\n\n"
                "pip install pytesseract\n"
                "And install Tesseract from:\n"
                "https://github.com/tesseract-ocr/tesseract"
            )
            return

        file_path = filedialog.askopenfilename(
            title="Select Receipt Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.log_status(f"Processing image: {os.path.basename(file_path)}")
            try:
                # Open and process image
                image = Image.open(file_path)

                # Perform OCR
                text = pytesseract.image_to_string(image)

                # Try to find survey code pattern (typically numeric)
                # Common patterns: XXXX-XXXX-XXXX or just numbers
                patterns = [
                    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # XXXX-XXXX-XXXX
                    r'\b\d{12,16}\b',  # Long number
                    r'\b\d{4,6}\b'  # Short code
                ]

                code = None
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    if matches:
                        code = matches[0].replace('-', '').replace(' ', '')
                        break

                if code:
                    self.code_entry.delete(0, tk.END)
                    self.code_entry.insert(0, code)
                    self.log_status(f"Found survey code: {code}")
                else:
                    self.log_status("Could not find survey code in image.")
                    messagebox.showwarning(
                        "Code Not Found",
                        "Could not detect a survey code in the image.\n"
                        "Please enter the code manually."
                    )

            except Exception as e:
                self.log_status(f"Error processing image: {str(e)}")
                messagebox.showerror("Error", f"Failed to process image:\n{str(e)}")

    def start_survey(self):
        """Start the survey automation"""
        if not SELENIUM_AVAILABLE:
            messagebox.showerror(
                "Selenium Not Available",
                "Please install selenium:\n\npip install selenium"
            )
            return

        survey_code = self.code_entry.get().strip()
        if not survey_code:
            messagebox.showwarning("Missing Code", "Please enter a survey code.")
            return

        self.is_running = True

        # Run automation in separate thread
        thread = threading.Thread(target=self.run_automation, args=(survey_code,))
        thread.daemon = True
        thread.start()

    def stop_survey(self):
        """Stop the survey automation"""
        self.is_running = False
        self.log_status("Stopping automation...")

        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass

        self.log_status("Automation stopped.")

    def run_automation(self, survey_code):
        """Main automation logic"""
        try:
            self.log_status("Initializing browser...")

            # Setup Chrome options
            options = Options()
            if self.headless_var.get():
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")

            # Initialize driver
            self.driver = webdriver.Chrome(options=options)

            self.log_status("Opening TellTims survey...")
            self.driver.get("https://telltims.ca/")

            # Wait for page to load
            time.sleep(3)

            # Switch to iframe if present
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                self.driver.switch_to.frame(iframe)
                self.log_status("Switched to survey iframe")
            except Exception as e:
                self.log_status("No iframe found, continuing on main page")

            # Wait for survey to load
            time.sleep(2)

            # Enter survey code
            self.log_status(f"Entering survey code: {survey_code}")
            self.enter_survey_code(survey_code)

            # Navigate through survey
            self.navigate_survey()

            self.log_status("Survey automation completed!")

        except Exception as e:
            self.log_status(f"Error: {str(e)}")
        finally:
            if self.driver and not self.is_running:
                try:
                    self.driver.quit()
                except:
                    pass

    def enter_survey_code(self, code):
        """Enter the survey code into the form"""
        delay = self.speed_var.get()

        # Try to find input field
        try:
            # Use Tab to navigate to first input
            body = self.driver.find_element(By.TAG_NAME, "body")

            # Tab to the code input field
            for _ in range(5):  # Tab a few times to reach input
                body.send_keys(Keys.TAB)
                time.sleep(delay * 0.3)

            # Enter the code
            active = self.driver.switch_to.active_element
            active.send_keys(code)
            self.log_status("Code entered")

            time.sleep(delay)

            # Press Tab to move to Next button and Enter to click
            active.send_keys(Keys.TAB)
            time.sleep(delay * 0.5)

            active = self.driver.switch_to.active_element
            active.send_keys(Keys.ENTER)
            self.log_status("Submitted code")

            time.sleep(delay * 2)

        except Exception as e:
            self.log_status(f"Error entering code: {str(e)}")

    def navigate_survey(self):
        """Navigate through survey questions using Tab and Enter"""
        delay = self.speed_var.get()
        max_questions = 50  # Safety limit
        question_count = 0

        while self.is_running and question_count < max_questions:
            try:
                time.sleep(delay)

                body = self.driver.find_element(By.TAG_NAME, "body")

                if self.auto_answer_var.get():
                    # Tab to select first option
                    for _ in range(3):
                        body.send_keys(Keys.TAB)
                        time.sleep(delay * 0.3)

                    # Press Space/Enter to select option
                    active = self.driver.switch_to.active_element
                    active.send_keys(Keys.SPACE)
                    time.sleep(delay * 0.5)

                # Tab to Next button
                for _ in range(5):
                    body.send_keys(Keys.TAB)
                    time.sleep(delay * 0.2)

                # Press Enter to proceed
                active = self.driver.switch_to.active_element
                active.send_keys(Keys.ENTER)

                question_count += 1
                self.log_status(f"Completed question {question_count}")

                time.sleep(delay)

                # Check if survey is complete (look for completion indicators)
                page_source = self.driver.page_source.lower()
                if any(phrase in page_source for phrase in [
                    "thank you", "survey complete", "completed",
                    "validation code", "coupon code"
                ]):
                    self.log_status("Survey appears to be complete!")
                    break

            except Exception as e:
                self.log_status(f"Navigation step: {str(e)}")
                # Continue trying
                time.sleep(delay)

        self.log_status(f"Navigation finished after {question_count} questions")


def main():
    """Main entry point"""
    root = tk.Tk()

    # Set app icon (Tim Hortons theme)
    try:
        # You could add a custom icon here
        pass
    except:
        pass

    app = TellTimsAutomator(root)

    # Handle window close
    def on_closing():
        if app.driver:
            try:
                app.driver.quit()
            except:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

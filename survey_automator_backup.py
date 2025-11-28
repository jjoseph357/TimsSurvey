#!/usr/bin/env python3
"""
TellTims Survey Automator
A visually appealing GUI application to automatically navigate through the TellTims survey.
Supports manual code entry, image upload OCR, and camera capture.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import re
import os
import tempfile
import numpy as np

# Optional imports with graceful fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import cv2
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
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
        radius = 10
        self.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill=color, outline=color)
        self.create_arc(self.width-radius*2, 0, self.width, radius*2, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, self.height-radius*2, radius*2, self.height, start=180, extent=90, fill=color, outline=color)
        self.create_arc(self.width-radius*2, self.height-radius*2, self.width, self.height, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(radius, 0, self.width-radius, self.height, fill=color, outline=color)
        self.create_rectangle(0, radius, self.width, self.height-radius, fill=color, outline=color)
        self.create_text(self.width//2, self.height//2, text=self.text,
                        fill=self.text_color, font=("Helvetica", 12, "bold"))

    def on_enter(self, event):
        self.draw_button(self.hover_color)

    def on_leave(self, event):
        self.draw_button(self.bg_color)

    def on_click(self, event):
        if self.command:
            self.command()


class CameraWindow(tk.Toplevel):
    """Camera capture window"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Camera Capture")
        self.geometry("700x620")
        self.resizable(False, False)
        self.callback = callback
        self.captured_image = None

        # Colors
        self.bg_color = "#f5f5f5"
        self.primary_color = "#c8102e"

        self.configure(bg=self.bg_color)

        # Header
        header = tk.Frame(self, bg=self.primary_color, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="Capture Receipt", font=("Helvetica", 18, "bold"),
                fg="white", bg=self.primary_color).pack(pady=15)

        # Video frame
        self.video_label = tk.Label(self, bg="#000000", width=640, height=480)
        self.video_label.pack(pady=20, padx=20)

        # Buttons - using standard tk.Button for reliability
        btn_frame = tk.Frame(self, bg=self.bg_color)
        btn_frame.pack(pady=10)

        # Style for buttons
        style = ttk.Style()
        style.configure("Capture.TButton", font=("Helvetica", 11, "bold"))

        self.capture_btn = tk.Button(
            btn_frame, text="CAPTURE", command=self.capture_image,
            bg=self.primary_color, fg="white", font=("Helvetica", 11, "bold"),
            width=12, height=2, relief=tk.RAISED, cursor="hand2"
        )
        self.capture_btn.pack(side=tk.LEFT, padx=10)

        self.use_btn = tk.Button(
            btn_frame, text="USE IMAGE", command=self.use_image,
            bg="#4a2c2a", fg="white", font=("Helvetica", 11, "bold"),
            width=12, height=2, relief=tk.RAISED, cursor="hand2"
        )
        self.use_btn.pack(side=tk.LEFT, padx=10)

        cancel_btn = tk.Button(
            btn_frame, text="CANCEL", command=self.cancel,
            bg="#666666", fg="white", font=("Helvetica", 11, "bold"),
            width=10, height=2, relief=tk.RAISED, cursor="hand2"
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)

        # Instructions
        tk.Label(self, text="Position the receipt code in view and click Capture",
                font=("Helvetica", 9), fg="#666666", bg=self.bg_color).pack(pady=5)

        # Initialize camera
        self.cap = None
        self.is_running = True
        
        # Handle window close - MUST be done before potential destruction
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        if not self.start_camera():
            self.destroy()
            return

    def start_camera(self):
        """Start camera feed, trying multiple indices and backends"""
        if not CAMERA_AVAILABLE:
            messagebox.showerror("Error", "OpenCV not available. Install with: pip install opencv-python")
            return False

        # Try indices 0, 1 with default backend first
        for index in range(2):
            try:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.cap = cap
                        self.update_frame()
                        return True
                    cap.release()
            except Exception:
                pass

        # Try indices 0, 1 with DirectShow (Windows specific)
        for index in range(2):
            try:
                cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.cap = cap
                        self.update_frame()
                        return True
                    cap.release()
            except Exception:
                pass
        
        messagebox.showerror("Error", "Could not open any camera (tried default and DirectShow backends)")
        return False

    def update_frame(self):
        """Update camera frame"""
        if self.is_running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Draw overlay guide
                height, width = frame.shape[:2]
                
                # Define box dimensions (centered, wide enough for code)
                box_w = int(width * 0.8)
                box_h = int(height * 0.2)
                x1 = int((width - box_w) / 2)
                y1 = int((height - box_h) / 2)
                x2 = x1 + box_w
                y2 = y1 + box_h
                
                # Create a copy for transparency
                overlay = frame.copy()
                
                # Draw semi-transparent box (white-ish)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), -1)
                alpha = 0.3
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                
                # Draw border (Red)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                
                # Draw text
                cv2.putText(frame, "ALIGN CODE HERE", (x1 + 10, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Convert to RGB for tkinter
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_rgb = cv2.resize(frame_rgb, (640, 480))

                # Convert to PhotoImage
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)

                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

                self.current_frame = frame

            self.after(30, self.update_frame)

    def capture_image(self):
        """Capture current frame and crop to guide box"""
        if hasattr(self, 'current_frame'):
            # Calculate ROI (same as in update_frame)
            height, width = self.current_frame.shape[:2]
            box_w = int(width * 0.8)
            box_h = int(height * 0.2)
            x1 = int((width - box_w) / 2)
            y1 = int((height - box_h) / 2)
            x2 = x1 + box_w
            y2 = y1 + box_h

            # Crop the image to the box
            self.captured_image = self.current_frame[y1:y2, x1:x2].copy()

            # Show captured image instead of live feed
            frame_rgb = cv2.cvtColor(self.captured_image, cv2.COLOR_BGR2RGB)
            frame_rgb = cv2.resize(frame_rgb, (640, 480))
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

    def use_image(self):
        """Use captured image for OCR"""
        if self.captured_image is not None:
            # Save to temp file
            temp_path = tempfile.mktemp(suffix='.png')
            cv2.imwrite(temp_path, self.captured_image)

            self.cleanup()
            self.callback(temp_path)
            self.destroy()
        else:
            messagebox.showwarning("No Image", "Please capture an image first")

    def cancel(self):
        """Cancel and close window"""
        self.cleanup()
        self.destroy()

    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        if self.cap:
            self.cap.release()


class TellTimsAutomator:
    """Main application class for TellTims Survey Automator"""

    def __init__(self, root):
        self.root = root
        self.root.title("TellTims Survey Automator")
        self.root.geometry("600x750")
        self.root.resizable(False, False)

        # Colors - Tim Hortons theme
        self.bg_color = "#f5f5f5"
        self.primary_color = "#c8102e"
        self.secondary_color = "#4a2c2a"
        self.accent_color = "#ffffff"

        self.root.configure(bg=self.bg_color)

        self.driver = None
        self.is_running = False
        self.validation_code = None

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

        # Image buttons frame
        img_btn_frame = tk.Frame(code_section, bg=self.bg_color)
        img_btn_frame.pack(pady=10)

        # Camera button
        camera_btn = ModernButton(
            img_btn_frame,
            text="Take Photo",
            command=self.open_camera,
            bg_color="#4a2c2a",
            hover_color="#3a1c1a",
            width=120
        )
        camera_btn.pack(side=tk.LEFT, padx=5)

        # Upload button
        upload_btn = ModernButton(
            img_btn_frame,
            text="Upload Image",
            command=self.upload_image,
            bg_color="#4a2c2a",
            hover_color="#3a1c1a",
            width=120
        )
        upload_btn.pack(side=tk.LEFT, padx=5)

        # Dependency status
        status_text = []
        if not OCR_AVAILABLE:
            status_text.append("OCR: pytesseract")
        if not CAMERA_AVAILABLE:
            status_text.append("Camera: opencv-python")
        if status_text:
            dep_warning = tk.Label(
                code_section,
                text=f"Missing: {', '.join(status_text)}",
                font=("Helvetica", 8),
                fg="#ff6b6b",
                bg=self.bg_color
            )
            dep_warning.pack()

        # Settings section
        settings_section = tk.LabelFrame(
            content_frame,
            text=" Settings ",
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

        self.speed_var = tk.DoubleVar(value=0.05)
        speed_slider = ttk.Scale(
            speed_frame,
            from_=0.05,
            to=2.0,
            variable=self.speed_var,
            orient=tk.HORIZONTAL
        )
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        tk.Label(speed_frame, text="Slow", font=("Helvetica", 8),
                bg=self.bg_color, fg="#888").pack(side=tk.LEFT)

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
        button_frame.pack(pady=15)

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

        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)

        # Footer
        footer_label = tk.Label(
            self.root,
            text="Use responsibly. For educational purposes only.",
            font=("Helvetica", 8),
            fg="#888888",
            bg=self.bg_color
        )
        footer_label.pack(pady=10)

        self.log_status("Ready. Enter survey code or capture/upload image.")

    def log_status(self, message):
        """Log a message to the status text area"""
        self.status_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()

    def open_camera(self):
        """Open camera capture window"""
        if not CAMERA_AVAILABLE:
            messagebox.showerror(
                "Camera Not Available",
                "Please install opencv-python:\n\npip install opencv-python"
            )
            return

        if not OCR_AVAILABLE:
            messagebox.showerror(
                "OCR Not Available",
                "Please install pytesseract:\n\npip install pytesseract"
            )
            return

        CameraWindow(self.root, self.process_captured_image)

    def process_captured_image(self, image_path):
        """Process image captured from camera"""
        self.log_status("Processing captured image...")
        self.scan_image(image_path)
        
        # Clean up temp file
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass

    def upload_image(self):
        """Handle image upload for OCR"""
        if not OCR_AVAILABLE:
            messagebox.showerror(
                "OCR Not Available",
                "Please install pytesseract and Tesseract OCR"
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
            self.log_status(f"Processing: {os.path.basename(file_path)}")
            self.scan_image(file_path)

    def scan_image(self, image_path):
        """Run OCR on image with multiple preprocessing steps"""
        # Tesseract config: Assume single uniform block of text (good for receipts)
        custom_config = r'--oem 3 --psm 6'
        
        try:
            # 1. Try original image first
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, config=custom_config)
            code = self.extract_code_from_text(text)
            
            if code:
                self.on_code_found(code, "Original")
                return

            # 2. Try OpenCV preprocessing if available
            if CAMERA_AVAILABLE: # Reusing cv2 import check
                self.log_status("Trying advanced preprocessing...")
                img_cv = cv2.imread(image_path)
                
                # Strategy A: Grayscale + Resize
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                # Resize to make text bigger (often helps OCR)
                scale = 2.0 # Increased scale
                width = int(gray.shape[1] * scale)
                height = int(gray.shape[0] * scale)
                resized = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)
                
                text = pytesseract.image_to_string(resized, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "Grayscale+Resize")
                    return

                # Strategy B: Thresholding (Binary)
                _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                text = pytesseract.image_to_string(thresh, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "Threshold")
                    return
                
                # Strategy C: Adaptive Thresholding (Gaussian)
                adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                            cv2.THRESH_BINARY, 11, 2)
                text = pytesseract.image_to_string(adapt, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "Adaptive Thresh")
                    return
                    
                # Strategy D: Gaussian Blur + Threshold (Denoising)
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                _, blur_thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                text = pytesseract.image_to_string(blur_thresh, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "Blur+Otsu")
                    return

                # Strategy E: CLAHE + Erosion (Fix saturation/faint text)
                # CLAHE (Contrast Limited Adaptive Histogram Equalization)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                cl1 = clahe.apply(gray)
                
                # Thresholding
                _, clahe_thresh = cv2.threshold(cl1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Morphological Erosion (Thickens black text by eroding white background)
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
                eroded = cv2.erode(clahe_thresh, kernel, iterations=1)
                
                text = pytesseract.image_to_string(eroded, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "CLAHE+Erosion")
                    return

                # Strategy F: Sharpening (Fix blur)
                kernel = np.array([[-1,-1,-1], 
                                 [-1, 9,-1], 
                                 [-1,-1,-1]])
                sharpened = cv2.filter2D(gray, -1, kernel)
                _, sharp_thresh = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                text = pytesseract.image_to_string(sharp_thresh, config=custom_config)
                code = self.extract_code_from_text(text)
                if code:
                    self.on_code_found(code, "Sharpening")
                    return

            self.log_status("Could not find survey code in image.")
            messagebox.showwarning("Code Not Found",
                "Could not detect a survey code after multiple attempts.\nPlease enter manually.")

        except Exception as e:
            self.log_status(f"Error during OCR: {str(e)}")

    def on_code_found(self, code, method):
        """Handle successful code detection"""
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, code)
        self.log_status(f"Found code ({method}): {code}")
        messagebox.showinfo("Success", f"Survey code detected!\n\nCode: {code}")

    def extract_code_from_text(self, text):
        """Extract survey code from OCR text using robust methods"""
        
        # Method 1: Regex patterns (Standard)
        patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{5}\b', # 4-4-4-4-5
            r'\b\d{21}\b',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                clean_code = matches[0].replace('-', '').replace(' ', '')
                if len(clean_code) == 21:
                    return clean_code
        
        # Method 2: Brute Force Digit Extraction
        # Remove everything except digits
        digits_only = re.sub(r'\D', '', text)
        
        # Look for a sequence of 21 digits in the stream
        # This handles cases where the code is split across lines or has weird symbols
        match = re.search(r'\d{21}', digits_only)
        if match:
            return match.group(0)
            
        return None

    def start_survey(self):
        """Start the survey automation"""
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("Selenium Not Available",
                "Please install selenium:\n\npip install selenium")
            return

        survey_code = self.code_entry.get().strip()
        if not survey_code:
            messagebox.showwarning("Missing Code", "Please enter a survey code.")
            return

        self.is_running = True
        self.validation_code = None

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

    def click_element_by_id(self, element_id, timeout=15):
        """Click element by ID using JavaScript (handles special characters in IDs)"""
        # Wait for element to be present
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script(f"return document.getElementById('{element_id}') !== null")
        )
        # Click using JavaScript
        self.driver.execute_script(f"""
            var element = document.getElementById('{element_id}');
            if (element) {{
                element.scrollIntoView(true);
                element.click();
            }}
        """)
        time.sleep(0.3)

    def wait_and_click(self, by, value, timeout=15):
        """Wait for element to be visible and clickable, then click it"""
        # First wait for element to be present
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        # Then wait for it to be visible
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
        # Finally wait for it to be clickable
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        # Scroll element into view
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.3)
        element.click()
        return element

    def wait_for_element(self, by, value, timeout=15):
        """Wait for element to be present and visible"""
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )

    def wait_for_page_load(self):
        """Wait for page to fully load"""
        # Wait for document ready state
        WebDriverWait(self.driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Small additional delay for dynamic content
        time.sleep(0.5)

    def click_next(self):
        """Click the Next button and wait for next page"""
        delay = self.speed_var.get()
        self.wait_and_click(By.ID, "NextButton")
        time.sleep(delay)
        self.wait_for_page_load()

    def run_automation(self, survey_code):
        """Main automation logic with specific element selectors"""
        try:
            self.log_status("Initializing browser...")

            options = Options()
            if self.headless_var.get():
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")

            self.driver = webdriver.Chrome(options=options)
            delay = self.speed_var.get()

            self.log_status("Opening TellTims survey...")
            self.driver.get("https://telltims.ca/")
            time.sleep(3)

            # Switch to iframe
            try:
                iframe = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                self.driver.switch_to.frame(iframe)
                self.log_status("Switched to survey iframe")
            except:
                self.log_status("No iframe found")

            time.sleep(2)

            # Page 1: Enter survey code
            self.log_status(f"Entering survey code: {survey_code}")
            self.wait_for_page_load()
            code_input = self.wait_for_element(By.ID, "QR~QID9")
            code_input.clear()
            code_input.send_keys(survey_code)
            self.click_next()
            self.log_status("Code submitted")

            # Page 2: Click Yes
            self.log_status("Selecting 'Yes'...")
            self.wait_for_page_load()
            self.click_element_by_id("QR~QID14~1")
            self.click_next()

            # Page 3: Click Highly Satisfied
            self.log_status("Selecting 'Highly Satisfied'...")
            self.click_element_by_id("QR~QID15~4")
            self.click_next()

            # Page 4: Enter text "Customer service"
            self.log_status("Entering feedback text...")
            self.wait_for_page_load()
            textarea = self.wait_for_element(By.ID, "QR~QID45")
            textarea.clear()
            textarea.send_keys("Customer service")
            self.click_next()

            # Page 5: Select Dine-In
            self.log_status("Selecting 'Dine-In'...")
            self.click_element_by_id("QR~QID18~5")
            self.click_next()

            # Page 6: Select Front counter
            self.log_status("Selecting 'Front counter'...")
            self.click_element_by_id("QR~QID19~5")
            self.click_next()

            # Page 7: Select Beverage only
            self.log_status("Selecting 'Beverage only'...")
            self.click_element_by_id("QR~QID20~5")
            self.click_next()

            # Page 8: Select Highly Satisfied for all 6 rows
            self.log_status("Rating all items 'Highly Satisfied'...")
            satisfaction_ids = [
                "QR~QID23~4~1", "QR~QID23~6~1", "QR~QID23~7~1",
                "QR~QID23~8~1", "QR~QID23~10~1", "QR~QID23~11~1"
            ]
            for radio_id in satisfaction_ids:
                try:
                    self.click_element_by_id(radio_id)
                    time.sleep(delay * 0.1)
                except Exception as e:
                    self.log_status(f"Could not find {radio_id}: {e}")
            self.click_next()

            # Page 9: Click Next (empty page)
            self.log_status("Proceeding...")
            self.click_next()

            # Page 10: Select No
            self.log_status("Selecting 'No'...")
            self.click_element_by_id("QR~QID151~3")
            self.click_next()

            # Page 11: Select Highly Likely for both rows
            self.log_status("Selecting 'Highly Likely'...")
            self.click_element_by_id("QR~QID44~1~1")
            time.sleep(delay * 0.3)
            self.click_element_by_id("QR~QID44~3~1")
            self.click_next()

            # Page 12: Select No (QID37)
            self.log_status("Selecting 'No'...")
            self.click_element_by_id("QR~QID37~2")
            self.click_next()

            # Page 13: Select No (QID134)
            self.log_status("Selecting 'No'...")
            self.click_element_by_id("QR~QID134~2")
            self.click_next()

            # Page 14: Select Yes (QID150)
            self.log_status("Selecting 'Yes'...")
            self.click_element_by_id("QR~QID150~2")
            self.click_next()

            # Page 15: Select "Something else" checkbox
            self.log_status("Selecting 'Something else'...")
            self.click_element_by_id("QR~QID48~5")
            self.click_next()

            # Page 16: Select No (QID68)
            self.log_status("Selecting 'No'...")
            self.click_element_by_id("QR~QID68~2")
            self.click_next()

            # Final page - Show validation code in browser
            self.log_status("Survey complete! Validation code displayed in browser.")
            self.log_status("Automation completed successfully!")

        except TimeoutException as e:
            self.log_status(f"Timeout waiting for element: {str(e)}")
        except Exception as e:
            self.log_status(f"Error: {str(e)}")
        finally:
            self.is_running = False


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TellTimsAutomator(root)

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

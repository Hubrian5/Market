import time
import cv2
import numpy as np
import pyautogui
from mss import mss
import easyocr

# ------------------- CONFIGURATION -------------------
# Screen region containing the numeric text
REGION = {"top": 1295, "left": 2005, "width": 185, "height": 65}

# Coordinates to click
CLICK_X, CLICK_Y = 2419, 1334

# Numeric threshold
THRESHOLD_VALUE = 19000

# OCR Reader (English, GPU optional)
reader = easyocr.Reader(['en'], gpu=False)

# Initialize screen grabber
sct = mss()

# Prevent repeated clicks
has_clicked = False

print("Bot started. Scanning region for number below 19000...")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        # --- Capture the defined region ---
        screenshot = np.array(sct.grab(REGION))
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        # Optional preprocessing to improve OCR accuracy
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]

        # --- OCR to read number ---
        results = reader.readtext(gray, detail=0)

        if results:
            text = results[0].replace(",", "").strip()
            if text.isdigit():
                number = int(text)
                print(f"Detected number: {number}")

                if number < THRESHOLD_VALUE:
                    if not has_clicked:
                        pyautogui.click(CLICK_X, CLICK_Y)
                        print(f"Clicked at ({CLICK_X}, {CLICK_Y}) because {number} < {THRESHOLD_VALUE}")
                        has_clicked = True
                else:
                    has_clicked = False  # reset when number rises again
            else:
                print(f"OCR result not numeric: '{results[0]}'")
        else:
            print("No number detected")

        time.sleep(0.25)  # scanning frequency

except KeyboardInterrupt:
    print("\nBot stopped by user.")

import time
import cv2
import numpy as np
import pyautogui
from mss import mss
import easyocr

# ------------------- INTERACTIVE CONFIGURATION -------------------
print("=== Price Watcher Bot ===")

def get_mouse_position(prompt):
    """Ask user to move mouse and press Enter to capture position."""
    print(prompt)
    input("Press Enter when ready...")
    pos = pyautogui.position()
    print(f"Captured: ({pos.x}, {pos.y})\n")
    return pos

use_custom_config = input("Do you want to configure the screen region and click position manually? (y/n): ").strip().lower()

if use_custom_config == 'y':
    print("\n--- Configure Region ---")
    top_left = get_mouse_position("Move your mouse to the TOP-LEFT corner of the region.")
    bottom_right = get_mouse_position("Now move your mouse to the BOTTOM-RIGHT corner of the region.")

    REGION = {
        "top": top_left.y,
        "left": top_left.x,
        "width": bottom_right.x - top_left.x,
        "height": bottom_right.y - top_left.y
    }

    print("--- Configure Click Position ---")
    click_pos = get_mouse_position("Move your mouse to the position you want to click (e.g., Buy button).")

    CLICK_X, CLICK_Y = click_pos.x, click_pos.y

    print(f"\n✅ Region set to: {REGION}")
    print(f"✅ Click coordinates set to: ({CLICK_X}, {CLICK_Y})\n")

else:
    REGION = {"top": 1295, "left": 2005, "width": 185, "height": 65}
    CLICK_X, CLICK_Y = 2419, 1334
    print(f"Using default region: {REGION}")
    print(f"Using default click coordinates: ({CLICK_X}, {CLICK_Y})\n")

# ------------------- OTHER CONFIGURATION -------------------
THRESHOLD_VALUE = 19000
SCAN_INTERVAL = 0.5  # seconds

# OCR setup
reader = easyocr.Reader(['en'], gpu=False)
sct = mss()

# Click control
has_clicked = False
last_number = None

print("Bot started. Scanning region for number below threshold...")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        # --- Capture region ---
        screenshot = np.array(sct.grab(REGION))
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]

        # --- OCR ---
        results = reader.readtext(gray, detail=0)

        if results:
            text = results[0].replace(",", "").strip()
            if text.isdigit():
                number = int(text)

                if number != last_number:
                    print(f"Detected number: {number}")
                    last_number = number

                # --- Click logic ---
                if number < THRESHOLD_VALUE and not has_clicked:
                    pyautogui.click(CLICK_X, CLICK_Y)
                    print(f"✅ Clicked at ({CLICK_X}, {CLICK_Y}) because {number} < {THRESHOLD_VALUE}")
                    has_clicked = True

                elif number >= THRESHOLD_VALUE:
                    # Reset click once price rises again
                    has_clicked = False
            else:
                print(f"OCR not numeric: '{results[0]}'")
        else:
            print("No number detected")

        time.sleep(SCAN_INTERVAL)

except KeyboardInterrupt:
    print("\n🛑 Bot stopped by user.")

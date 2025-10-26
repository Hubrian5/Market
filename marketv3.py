import time
import cv2
import numpy as np
import pyautogui
from mss import mss
import easyocr
import json
import os
import threading
import keyboard  # for global hotkey detection

CONFIG_FILE = "config.json"

# ------------------- HELPER FUNCTIONS -------------------
def get_mouse_position(prompt):
    print(prompt)
    input("Press Enter when ready...")
    pos = pyautogui.position()
    print(f"Captured: ({pos.x}, {pos.y})\n")
    return pos

def save_config(region, click_coords):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"REGION": region, "CLICK_X": click_coords[0], "CLICK_Y": click_coords[1]}, f)
    print(f"✅ Configuration saved to {CONFIG_FILE}\n")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        print(f"✅ Loaded configuration from {CONFIG_FILE}\n")
        return data["REGION"], (data["CLICK_X"], data["CLICK_Y"])
    return None, None

# ------------------- CONFIGURATION -------------------
print("=== Price Watcher Bot ===")

REGION, click_coords = load_config()

if REGION and click_coords:
    use_existing = input("Use saved configuration? (y/n): ").strip().lower()
    if use_existing != 'y':
        REGION = None

if not REGION or not click_coords:
    print("\n--- Configure Region ---")
    top_left = get_mouse_position("Move your mouse to the TOP-LEFT corner of the region.")
    bottom_right = get_mouse_position("Move your mouse to the BOTTOM-RIGHT corner of the region.")

    REGION = {
        "top": top_left.y,
        "left": top_left.x,
        "width": bottom_right.x - top_left.x,
        "height": bottom_right.y - top_left.y
    }

    print("--- Configure Purchase Button ---")
    click_pos = get_mouse_position("Move your mouse to the position you want to click to purchase (e.g., Buy button).")
    click_coords = (click_pos.x, click_pos.y)

    save_config(REGION, click_coords)

CLICK_X, CLICK_Y = click_coords
print(f"Using region: {REGION}")
print(f"Using purchase click coordinates: ({CLICK_X}, {CLICK_Y})\n")

# ------------------- CONSTANTS -------------------
THRESHOLD_VALUE = 19000
SCAN_INTERVAL = 0.75

ITEM_X, ITEM_Y = 640, 285
RETURN_X, RETURN_Y = 660, 200

reader = easyocr.Reader(['en'], gpu=False)
sct = mss()

last_number = None
purchase_made = False
running = True

print("Bot started. Press Ctrl+C OR F8 to stop (works globally).\n")

# ------------------- GLOBAL HOTKEY HANDLER -------------------
def monitor_hotkey():
    global running
    keyboard.add_hotkey('ctrl+c', lambda: stop_bot())
    keyboard.add_hotkey('f8', lambda: stop_bot())
    while running:
        time.sleep(0.1)

def stop_bot():
    global running
    running = False
    print("\n🛑 Stop signal received. Stopping bot safely...")

# Run hotkey listener in background thread
threading.Thread(target=monitor_hotkey, daemon=True).start()

# ------------------- MAIN LOOP -------------------
try:
    while running:
        pyautogui.click(ITEM_X, ITEM_Y)
        print(f"🟦 Opened item at ({ITEM_X}, {ITEM_Y})")
        time.sleep(0.2)

        screenshot = np.array(sct.grab(REGION))
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]

        results = reader.readtext(gray, detail=0)

        if results:
            text = results[0].replace(",", "").strip()
            if text.isdigit():
                number = int(text)
                if number != last_number:
                    print(f"Detected number: {number}")
                    last_number = number

                if number <= THRESHOLD_VALUE:
                    pyautogui.click(CLICK_X, CLICK_Y)
                    print(f"✅ Purchased item because {number} ≤ {THRESHOLD_VALUE}")
                    purchase_made = True
                    time.sleep(0.01)
                else:
                    pyautogui.click(RETURN_X, RETURN_Y)
                    print(f"↩️ Returned (price {number} > {THRESHOLD_VALUE})")
                    purchase_made = False
                    time.sleep(0.01)
            else:
                print(f"OCR not numeric: '{results[0]}' — returning.")
                pyautogui.click(RETURN_X, RETURN_Y)
        else:
            print("No number detected — returning.")
            pyautogui.click(RETURN_X, RETURN_Y)

        time.sleep(SCAN_INTERVAL)

except Exception as e:
    print(f"\n❌ Error: {e}")

finally:
    print("Bot stopped.")

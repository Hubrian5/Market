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
    """Prompt user to capture mouse position."""
    print(prompt)
    input("Press Enter when ready...")
    pos = pyautogui.position()
    print(f"Captured: ({pos.x}, {pos.y})\n")
    return pos

def save_config(region, click_coords, item_coords, return_coords):
    """Save configuration data to JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "REGION": region,
            "CLICK_X": click_coords[0],
            "CLICK_Y": click_coords[1],
            "ITEM_X": item_coords[0],
            "ITEM_Y": item_coords[1],
            "RETURN_X": return_coords[0],
            "RETURN_Y": return_coords[1]
        }, f, indent=4)
    print(f"✅ Configuration saved to {CONFIG_FILE}\n")

def load_config():
    """Load configuration data from JSON if available."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        print(f"✅ Loaded configuration from {CONFIG_FILE}\n")
        region = data.get("REGION")
        click_coords = (data.get("CLICK_X"), data.get("CLICK_Y"))
        item_coords = (data.get("ITEM_X"), data.get("ITEM_Y"))
        return_coords = (data.get("RETURN_X"), data.get("RETURN_Y"))
        return region, click_coords, item_coords, return_coords
    return None, None, None, None

# ------------------- CONFIGURATION -------------------
print("=== Price Watcher Bot ===")

REGION, click_coords, item_coords, return_coords = load_config()

if REGION and click_coords and item_coords and return_coords:
    use_existing = input("Use saved configuration? (y/n): ").strip().lower()
    if use_existing != 'y':
        REGION = click_coords = item_coords = return_coords = None

if not REGION or not click_coords or not item_coords or not return_coords:
    print("\n--- Configure Region ---")
    top_left = get_mouse_position("Move your mouse to the TOP-LEFT corner of the price region.")
    bottom_right = get_mouse_position("Move your mouse to the BOTTOM-RIGHT corner of the price region.")

    REGION = {
        "top": top_left.y,
        "left": top_left.x,
        "width": bottom_right.x - top_left.x,
        "height": bottom_right.y - top_left.y
    }

    print("--- Configure Item Coordinates ---")
    item_pos = get_mouse_position("Move your mouse to the ITEM you want to check (e.g., item slot).")
    item_coords = (item_pos.x, item_pos.y)

    print("--- Configure Return Coordinates ---")
    return_pos = get_mouse_position("Move your mouse to the RETURN button or area.")
    return_coords = (return_pos.x, return_pos.y)

    print("--- Configure Purchase Button ---")
    click_pos = get_mouse_position("Move your mouse to the PURCHASE button (e.g., Buy button).")
    click_coords = (click_pos.x, click_pos.y)

    save_config(REGION, click_coords, item_coords, return_coords)

CLICK_X, CLICK_Y = click_coords
ITEM_X, ITEM_Y = item_coords
RETURN_X, RETURN_Y = return_coords

print(f"Using region: {REGION}")
print(f"Using purchase click coordinates: ({CLICK_X}, {CLICK_Y})")
print(f"Using item coordinates: ({ITEM_X}, {ITEM_Y})")
print(f"Using return coordinates: ({RETURN_X}, {RETURN_Y})\n")

# ------------------- CONSTANTS -------------------
THRESHOLD_VALUE = 19000
SCAN_INTERVAL = 0.75

reader = easyocr.Reader(['en'], gpu=False)
sct = mss()

last_number = None
purchase_made = False
running = True

print("Bot started. Press Ctrl+C OR F8 to stop (works globally).\n")

# ------------------- GLOBAL HOTKEY HANDLER -------------------
def stop_bot():
    global running
    running = False
    print("\n🛑 Stop signal received. Stopping bot safely...")

def monitor_hotkey():
    keyboard.add_hotkey('ctrl+c', stop_bot)
    keyboard.add_hotkey('f8', stop_bot)
    while running:
        time.sleep(0.1)

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

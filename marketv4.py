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

def save_config(follow_coords, item_coords, return_coords, click_coords, region, threshold):
    """Save configuration data to JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "FOLLOW_X": follow_coords[0],
            "FOLLOW_Y": follow_coords[1],
            "ITEM_X": item_coords[0],
            "ITEM_Y": item_coords[1],
            "RETURN_X": return_coords[0],
            "RETURN_Y": return_coords[1],
            "CLICK_X": click_coords[0],
            "CLICK_Y": click_coords[1],
            "REGION": region,
            "THRESHOLD_VALUE": threshold
        }, f, indent=4)
    print(f"✅ Configuration saved to {CONFIG_FILE}\n")

def load_config():
    """Load configuration data from JSON if available."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        print(f"✅ Loaded configuration from {CONFIG_FILE}\n")
        follow_coords = (data.get("FOLLOW_X"), data.get("FOLLOW_Y"))
        item_coords = (data.get("ITEM_X"), data.get("ITEM_Y"))
        return_coords = (data.get("RETURN_X"), data.get("RETURN_Y"))
        click_coords = (data.get("CLICK_X"), data.get("CLICK_Y"))
        region = data.get("REGION")
        threshold = data.get("THRESHOLD_VALUE", 19000)
        return follow_coords, item_coords, return_coords, click_coords, region, threshold
    return None, None, None, None, None, None

# ------------------- STARTUP -------------------
print("=== Price Watcher Bot ===")

choice = input("Would you like to configure (c) or run (r)? ").strip().lower()

if choice == "c":
    print("\n--- Configure Follow Coordinate ---")
    follow_pos = get_mouse_position("Move your mouse to the FOLLOW button and press Enter.")
    follow_coords = (follow_pos.x, follow_pos.y)

    print("\n--- Configure Item Coordinate ---")
    item_pos = get_mouse_position("Move your mouse to the ITEM slot and press Enter.")
    item_coords = (item_pos.x, item_pos.y)

    print("\n--- Configure Return Coordinate ---")
    return_pos = get_mouse_position("Move your mouse to the RETURN button and press Enter.")
    return_coords = (return_pos.x, return_pos.y)

    print("\n--- Configure Purchase Button Coordinate ---")
    click_pos = get_mouse_position("Move your mouse to the PURCHASE button and press Enter.")
    click_coords = (click_pos.x, click_pos.y)

    print("\n--- Configure Price Region ---")
    top_left = get_mouse_position("Move your mouse to the TOP-LEFT corner of the price region.")
    bottom_right = get_mouse_position("Move your mouse to the BOTTOM-RIGHT corner of the price region.")

    REGION = {
        "top": top_left.y,
        "left": top_left.x,
        "width": bottom_right.x - top_left.x,
        "height": bottom_right.y - top_left.y
    }

    THRESHOLD_VALUE = int(input("\nEnter threshold value (e.g., 19000): ").strip())

    save_config(follow_coords, item_coords, return_coords, click_coords, REGION, THRESHOLD_VALUE)
    print("✅ Configuration complete. You can now run the script again and choose 'r' to start.")
    exit(0)

# ------------------- LOAD CONFIG -------------------
follow_coords, item_coords, return_coords, click_coords, REGION, THRESHOLD_VALUE = load_config()

if not all([follow_coords, item_coords, return_coords, click_coords, REGION]):
    print("❌ Missing configuration. Please run again and choose configure (c).")
    exit(1)

FOLLOW_X, FOLLOW_Y = follow_coords
ITEM_X, ITEM_Y = item_coords
RETURN_X, RETURN_Y = return_coords
CLICK_X, CLICK_Y = click_coords

print(f"\nUsing configuration:")
print(f"Follow coordinates: ({FOLLOW_X}, {FOLLOW_Y})")
print(f"Item coordinates:   ({ITEM_X}, {ITEM_Y})")
print(f"Return coordinates: ({RETURN_X}, {RETURN_Y})")
print(f"Purchase button:    ({CLICK_X}, {CLICK_Y})")
print(f"Region:             {REGION}")
print(f"Threshold:          {THRESHOLD_VALUE}\n")

# ------------------- BOT SETTINGS -------------------
SCAN_INTERVAL = 0.75

reader = easyocr.Reader(['en'], gpu=False)
sct = mss()

last_number = None
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
        pyautogui.click(FOLLOW_X, FOLLOW_Y)
        print(f"🟨 Clicked follow at ({FOLLOW_X}, {FOLLOW_Y})")
        time.sleep(0.2)

        pyautogui.click(ITEM_X, ITEM_Y)
        print(f"🟦 Opened item at ({ITEM_X}, {ITEM_Y})")
        time.sleep(0.3)

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
                else:
                    pyautogui.click(RETURN_X, RETURN_Y)
                    print(f"↩️ Returned (price {number} > {THRESHOLD_VALUE})")
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

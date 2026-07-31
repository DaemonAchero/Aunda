import os
import json
import cv2
import mediapipe as mp
import math
import time
import threading
import queue
import numpy as np
import pyautogui
from playwright.sync_api import sync_playwright

# Disable PyAutoGUI fail-safe pause for real-time fluid cursor movement
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0

# Screen resolution for mouse mapping
SCREEN_W, SCREEN_H = pyautogui.size()

# Target path for custom TikTok cookie JSON file
STORAGE_STATE_PATH = r"D:\Jomnes\aunda\data.json"

# ----------------------------------------------
# Cursor Smoothing Configuration
# ----------------------------------------------
# Lower values = Smoother/Butter-like movement (e.g., 0.12 - 0.20)
# Higher values = Faster response/Less lag (e.g., 0.35 - 0.50)
SMOOTHING_FACTOR = 0.18 

# Ignores camera micro-shakes under this pixel distance threshold
DEADZONE_PIXELS = 2.5   

prev_cursor_x, prev_cursor_y = pyautogui.position()

def smooth_cursor_movement(target_x, target_y):
    """Applies Exponential Moving Average (EMA) and a deadzone filter for ultra-smooth cursor motion."""
    global prev_cursor_x, prev_cursor_y

    # Calculate distance from last position
    dist = math.hypot(target_x - prev_cursor_x, target_y - prev_cursor_y)
    
    # If movement is inside the deadzone, keep cursor completely stationary
    if dist < DEADZONE_PIXELS:
        return prev_cursor_x, prev_cursor_y

    # Exponential Moving Average (Interpolation)
    smooth_x = prev_cursor_x + (target_x - prev_cursor_x) * SMOOTHING_FACTOR
    smooth_y = prev_cursor_y + (target_y - prev_cursor_y) * SMOOTHING_FACTOR

    prev_cursor_x, prev_cursor_y = smooth_x, smooth_y
    return int(smooth_x), int(smooth_y)

# ----------------------------------------------
# Cookie Parsing Utility
# ----------------------------------------------
def load_tiktok_cookies(context, file_path):
    """Parses custom TikTok JSON structure and injects cookies into Playwright context."""
    if not os.path.exists(file_path):
        print(f"⚠️ Cookie file not found at '{file_path}'. Proceeding with clean browser state.")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_cookies = data.get("tiktok", [])
        formatted_cookies = []

        for c in raw_cookies:
            cookie = {
                "name": c.get("name"),
                "value": c.get("value"),
                "domain": c.get("domain", ".tiktok.com"),
                "path": c.get("path", "/"),
                "secure": c.get("secure", True),
                "httpOnly": c.get("httpOnly", True),
            }
            
            exp = c.get("expirationDate")
            if exp is not None:
                cookie["expires"] = float(exp)

            same_site = c.get("sameSite")
            if same_site in ["Strict", "Lax", "None"]:
                cookie["sameSite"] = same_site

            formatted_cookies.append(cookie)

        if formatted_cookies:
            context.add_cookies(formatted_cookies)
            print(f"✅ Loaded {len(formatted_cookies)} TikTok cookies from '{file_path}'.")
    except Exception as e:
        print(f"❌ Failed to parse or load cookies from '{file_path}': {e}")

# ----------------------------------------------
# Browser Automation Setup
# ----------------------------------------------
TARGET_URL = "https://www.tiktok.com"
command_queue = queue.Queue()

def launch_browser():
    """Runs Playwright with persistent session cookies injected."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-gpu-vsync",
                "--enable-features=SmoothScrolling"
            ]
        )
        context = browser.new_context(no_viewport=True)
        
        # Load and apply custom cookie state
        load_tiktok_cookies(context, STORAGE_STATE_PATH)

        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        while True:
            try:
                action, value = command_queue.get(timeout=0.02)
                
                if action == "NAVIGATE_URL":
                    page.goto(value, wait_until="domcontentloaded")

                elif action in ("SWIPE_DEFAULT", "SWIPE_REVERSED"):
                    direction = 1 if action == "SWIPE_DEFAULT" else -1
                    scroll_distance = 650 * direction

                    page.evaluate("""({ deltaY }) => {
                        const ytTarget = document.querySelector('ytd-app') || 
                                         document.querySelector('ytd-browse') || 
                                         document.querySelector('#primary') ||
                                         document.querySelector('body') ||
                                         document.documentElement;

                        if (ytTarget) {
                            if (typeof ytTarget.focus === 'function') {
                                ytTarget.focus();
                            }
                        }

                        const scrollTarget = document.querySelector('ytd-browse') ||
                                             document.querySelector('#primary') ||
                                             document.querySelector('[class*="-SetItemContainer"]') ||
                                             document.querySelector('#column-list-container') ||
                                             document.querySelector('main') ||
                                             document.querySelector('body') ||
                                             document.documentElement;

                        if (!scrollTarget) return;

                        let start = null;
                        const duration = 300;
                        const initialScroll = scrollTarget.scrollTop || window.scrollY;

                        function smoothStep(timestamp) {
                            if (!start) start = timestamp;
                            const progress = Math.min((timestamp - start) / duration, 1);
                            const easeOut = 1 - Math.pow(1 - progress, 3);
                            const currentTargetPosition = initialScroll + (deltaY * easeOut);

                            if (scrollTarget === document.documentElement || scrollTarget === document.body) {
                                window.scrollTo(0, currentTargetPosition);
                            } else {
                                scrollTarget.scrollTop = currentTargetPosition;
                            }

                            if (progress < 1) {
                                window.requestAnimationFrame(smoothStep);
                            }
                        }

                        window.requestAnimationFrame(smoothStep);
                    }""", {"deltaY": scroll_distance})

                elif action == "SAVE_SESSION":
                    try:
                        active_cookies = context.cookies()
                        os.makedirs(os.path.dirname(STORAGE_STATE_PATH), exist_ok=True)
                        
                        out_data = {"tiktok": []}
                        for c in active_cookies:
                            out_data["tiktok"].append({
                                "name": c.get("name"),
                                "value": c.get("value"),
                                "domain": c.get("domain"),
                                "hostOnly": False,
                                "path": c.get("path"),
                                "secure": c.get("secure"),
                                "httpOnly": c.get("httpOnly"),
                                "sameSite": c.get("sameSite"),
                                "session": False,
                                "firstPartyDomain": "",
                                "partitionKey": None,
                                "expirationDate": c.get("expires"),
                                "storeId": None
                            })

                        with open(STORAGE_STATE_PATH, "w", encoding="utf-8") as f:
                            json.dump(out_data, f, indent=4)
                        print(f"✅ Saved active session cookies to '{STORAGE_STATE_PATH}'.")
                    except Exception as e:
                        print(f"❌ Failed to save session cookies: {e}")

                command_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"❌ Playwright Error: {e}")

browser_thread = threading.Thread(target=launch_browser, daemon=True)
browser_thread.start()

def send_command(action, value):
    command_queue.put((action, value))

# ----------------------------------------------
# MediaPipe & Tracking Setup
# ----------------------------------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.75
)
mp_draw = mp.solutions.drawing_utils

ZONES = ["top", "middle", "bottom"]
zone_index = 1
current_zone = ZONES[zone_index]

is_locked = False
bottom_points_active = False
active_point_index = 1
middle_reversed_active = False

fist_latched = False
index_pinch_latched = False
index_middle_click_latched = False
last_unlock_time = 0.0
last_click_time = 0.0
UNLOCK_COOLDOWN_SEC = 0.8
CLICK_DEBOUNCE_SEC = 0.3

prev_swipe_y = None
swipe_latched = False

TOUCH_THRESHOLD = 0.16
RELEASE_THRESHOLD = 0.30
SWIPE_UP_THRESHOLD = 0.035

# 2D Proximity threshold for Index (8) + Middle (12) click
CLICK_TOUCH_THRESHOLD_2D = 0.42

def dist_3d(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def dist_2d(p1, p2):
    """Calculates 2D Euclidean distance on the camera plane."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def check_fist_strict_mcp(lm):
    return (lm[8].y >= lm[5].y and 
            lm[12].y >= lm[9].y and 
            lm[16].y >= lm[13].y and 
            lm[20].y >= lm[17].y)

def reset_all_subfeatures():
    global bottom_points_active, active_point_index, middle_reversed_active, prev_swipe_y, swipe_latched
    bottom_points_active = False
    active_point_index = 1
    middle_reversed_active = False
    prev_swipe_y = None
    swipe_latched = False

def is_two_finger_up_pose(lm):
    return lm[8].y < lm[6].y and lm[12].y < lm[10].y

# ----------------------------------------------
# Left-Aligned Compact UI Overlay
# ----------------------------------------------
def draw_ui_compact_left(img, active_zone, locked, is_pt_active, active_pt, is_reversed):
    h, w = img.shape[:2]
    center_x = int(w * 0.08)
    
    y_top = int(h * 0.22)
    y_mid = int(h * 0.45)
    y_bot = int(h * 0.68)

    active_color = (0, 0, 255) if locked else (0, 180, 0)
    inactive_color = (180, 180, 180)

    # TOP POINT
    is_top = (active_zone == "top")
    cv2.circle(img, (center_x, y_top), 10 if is_top else 5, active_color if is_top else inactive_color, -1)
    if is_top:
        cv2.circle(img, (center_x, y_top), 15, active_color, 1)
        txt = "TOP (INDEX+MID TOUCH = CLICK)" if locked else "TOP"
        cv2.putText(img, txt, (center_x + 20, y_top + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, active_color, 1)

    # MIDDLE POINT
    is_mid = (active_zone == "middle")
    mid_color = (255, 0, 255) if (is_mid and is_reversed) else (active_color if is_mid else inactive_color)
    cv2.circle(img, (center_x, y_mid), 10 if is_mid else 5, mid_color, -1)
    if is_mid:
        cv2.circle(img, (center_x, y_mid), 15, mid_color, 1)
        txt = "MID (REV)" if is_reversed else "MID"
        cv2.putText(img, txt, (center_x + 20, y_mid + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, mid_color, 1)

    # BOTTOM POINT
    is_bot = (active_zone == "bottom")
    if is_bot and is_pt_active:
        labels = ["1:YOUTUBE", "2:TIKTOK", "3:SAVE COOKIE", "4:PT4", "5:CANCEL"]
        spacing = 58
        
        for i in range(1, 6):
            pt_x = center_x + (i - 1) * spacing
            selected = (active_pt == i)
            pt_color = (0, 165, 255) if selected else (150, 150, 150)
            
            cv2.circle(img, (pt_x, y_bot), 8 if selected else 5, pt_color, -1)
            if selected:
                cv2.circle(img, (pt_x, y_bot), 12, (0, 165, 255), 1)
            
            cv2.putText(img, labels[i-1], (pt_x - 12, y_bot + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (50, 50, 50), 1)
    else:
        cv2.circle(img, (center_x, y_bot), 10 if is_bot else 5, active_color if is_bot else inactive_color, -1)
        if is_bot:
            cv2.circle(img, (center_x, y_bot), 15, active_color, 1)
            cv2.putText(img, "BOT", (center_x + 20, y_bot + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, active_color, 1)

# ----------------------------------------------
# Main Loop
# ----------------------------------------------
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    
    current_time = time.time()
    in_cooldown = (current_time - last_unlock_time) < UNLOCK_COOLDOWN_SEC

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                canvas, 
                hand_landmarks, 
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(0, 150, 0), thickness=2)
            )
            lm = hand_landmarks.landmark

            # 3D Hand scale calculation (Wrist to Index MCP)
            hand_scale_3d = dist_3d(lm[0], lm[5])
            if hand_scale_3d == 0:
                hand_scale_3d = 0.1

            # 2D Hand scale calculation for planar proximity checks
            hand_scale_2d = dist_2d(lm[5], lm[17])
            if hand_scale_2d == 0:
                hand_scale_2d = 0.1

            # Standard Thumb-Index pinch distance for navigation/cycling
            index_thumb_dist = dist_3d(lm[4], lm[8]) / hand_scale_3d
            index_near_thumb = index_thumb_dist < TOUCH_THRESHOLD

            # Index Tip (8) + Middle Tip (12) 2D distance normalized by 2D hand scale
            index_middle_dist_2d = dist_2d(lm[8], lm[12]) / hand_scale_2d
            index_near_middle = index_middle_dist_2d < CLICK_TOUCH_THRESHOLD_2D

            is_fist = check_fist_strict_mcp(lm)

            # --- TOP ZONE SMOOTH CURSOR & SELECTION CONTROL ---
            if is_locked and current_zone == "top":
                raw_x = int(lm[8].x * SCREEN_W)
                raw_y = int(lm[8].y * SCREEN_H)
                
                # Apply EMA + Deadzone filtering for ultra-fluid movement
                smooth_x, smooth_y = smooth_cursor_movement(raw_x, raw_y)
                pyautogui.moveTo(smooth_x, smooth_y)

                # Direct trigger when index finger and middle finger are touching or close together
                if index_near_middle:
                    if not index_middle_click_latched and (current_time - last_click_time > CLICK_DEBOUNCE_SEC):
                        pyautogui.click()
                        index_middle_click_latched = True
                        last_click_time = current_time
                else:
                    if index_middle_dist_2d > RELEASE_THRESHOLD:
                        index_middle_click_latched = False

            # --- FIST GESTURE CONTROLLER ---
            if is_fist:
                if not fist_latched:
                    if is_locked and current_zone == "bottom" and bottom_points_active:
                        if active_point_index == 1:
                            send_command("NAVIGATE_URL", "https://www.youtube.com/")
                        elif active_point_index == 2:
                            send_command("NAVIGATE_URL", "https://www.tiktok.com/")
                        elif active_point_index == 3:
                            send_command("SAVE_SESSION", None)
                        elif active_point_index == 5:
                            pass

                        is_locked = False
                        last_unlock_time = time.time()
                        reset_all_subfeatures()
                        fist_latched = True

                    else:
                        if is_locked:
                            is_locked = False
                            last_unlock_time = time.time()
                        else:
                            if not in_cooldown:
                                is_locked = True

                        reset_all_subfeatures()
                        index_pinch_latched = True
                        fist_latched = True
            else:
                fist_latched = False

            # --- ZONE INTERACTIONS ---
            if is_locked:
                if current_zone == "bottom":
                    if index_near_thumb:
                        if not index_pinch_latched:
                            if not bottom_points_active:
                                bottom_points_active = True
                                active_point_index = 1
                            else:
                                active_point_index = (active_point_index % 5) + 1
                            
                            index_pinch_latched = True
                    else:
                        if index_thumb_dist > RELEASE_THRESHOLD:
                            index_pinch_latched = False

                elif current_zone == "middle":
                    if index_near_thumb:
                        if not index_pinch_latched:
                            middle_reversed_active = not middle_reversed_active
                            index_pinch_latched = True
                    else:
                        if index_thumb_dist > RELEASE_THRESHOLD:
                            index_pinch_latched = False

                    if is_two_finger_up_pose(lm):
                        curr_y = (lm[8].y + lm[12].y) / 2.0
                        if prev_swipe_y is not None:
                            delta_y = prev_swipe_y - curr_y
                            if delta_y > SWIPE_UP_THRESHOLD and not swipe_latched:
                                cmd = "SWIPE_REVERSED" if middle_reversed_active else "SWIPE_DEFAULT"
                                send_command(cmd, "SCROLL_DOM")
                                swipe_latched = True
                            elif delta_y < 0.005:
                                swipe_latched = False
                        prev_swipe_y = curr_y
                    else:
                        prev_swipe_y = None
                        swipe_latched = False

            else:
                if current_zone != "top":
                    if not in_cooldown:
                        if index_near_thumb:
                            if not index_pinch_latched:
                                zone_index = (zone_index + 1) % len(ZONES)
                                current_zone = ZONES[zone_index]
                                reset_all_subfeatures()
                                index_pinch_latched = True
                        else:
                            if index_thumb_dist > RELEASE_THRESHOLD:
                                index_pinch_latched = False
                    else:
                        if index_thumb_dist > RELEASE_THRESHOLD:
                            index_pinch_latched = False
                else:
                    if not in_cooldown and index_near_thumb and not index_pinch_latched:
                        zone_index = (zone_index + 1) % len(ZONES)
                        current_zone = ZONES[zone_index]
                        reset_all_subfeatures()
                        index_pinch_latched = True
                    elif index_thumb_dist > RELEASE_THRESHOLD:
                        index_pinch_latched = False

            break
    else:
        fist_latched = False
        index_pinch_latched = False
        index_middle_click_latched = False
        prev_swipe_y = None

    draw_ui_compact_left(canvas, current_zone, is_locked, bottom_points_active, active_point_index, middle_reversed_active)

    if is_locked:
        status_str = f"LOCKED ({current_zone.upper()})"
        color = (0, 0, 255)
    elif in_cooldown:
        time_left = max(0.0, UNLOCK_COOLDOWN_SEC - (current_time - last_unlock_time))
        status_str = f"UNLOCKED (WAIT {time_left:.1f}s)"
        color = (0, 120, 255)
    else:
        status_str = "UNLOCKED (READY)"
        color = (0, 180, 0)

    cv2.putText(canvas, f"State: {status_str}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Web DOM Gesture Control", canvas)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
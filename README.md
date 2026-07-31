<<<<<<< HEAD
```markdown
# Web DOM Hand Gesture Control with MediaPipe & Playwright (Beta Version)

An advanced, real-time hand gesture interaction system designed to control web browsing (TikTok, YouTube, etc.) and cursor movement using OpenCV, MediaPipe Hands, PyAutoGUI, and Playwright. 

---

## Demo Reference

* Local Video File: `D:\Jomnes\aunda\Demo.mp4`

---

## High-Level Architecture Flow Diagram


```

+-----------------------------------------------------------------------+
|                             CAMERA INPUT                              |
|                         (USB / Integrated WebCam)                     |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                         OPENCV CAPTURE LOOP                           |
|               Captures raw frame and flips horizontally               |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                         MEDIAPIPE HANDS ENGINE                        |
|             Extracts 21 3D Hand Landmarks & Normalized Coordinates    |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                        ZONE & GESTURE DISPATCHER                      |
|                  Determines Frame Spatial Location & Pose             |
+-----------------------------------------------------------------------+
|                               |                               |
v                               v                               v
+--------------+               +----------------+              +--------------+
|   TOP ZONE   |               |  MIDDLE ZONE   |              | BOTTOM ZONE  |
| Mouse/Cursor |               | Feed Scrolling |              | Context Menu |
+--------------+               +----------------+              +--------------+
|                               |                               |
| Exponential Moving            | Normalized Y-Axis             | Sub-Item     |
| Average (EMA)                 | Delta Offset                  | Selection    |
v                               v                               v
+--------------+               +----------------+              +--------------+
|  PyAutoGUI   |               | Playwright DOM |              | Playwright / |
| Cursor Control|              | Mouse Wheel /  |              | Cookie Engine|
|  & Clicks    |               | Keyboard Key   |              | JSON Dump    |
+--------------+               +----------------+              +--------------+

```

---

## Key System Features

* **Exponential Moving Average (EMA) Cursor Smoothing**: Features an ultra-smooth tracking algorithm with deadzone filtering for fluid pointer interactions without cursor jitter.
* **Zone-Based Gesture Interface**: Splits the camera frame vertically into three dedicated functional zones (TOP, MIDDLE, BOTTOM) to isolate commands and prevent cross-triggering.
* **State Locking Mechanism**: Implements a strict binary lock/unlock model using explicit closed fist gestures to lock active zones and prevent unintended gesture execution.
* **Platform-Specific Navigation**: Optimized dedicated interactions for media feeds including TikTok video progression and YouTube Shorts control.
* **Persistent Session & Cookie Engine**: Reads and updates local session state to JSON storage (`D:\Jomnes\aunda\data.json`), maintaining authenticated logins across browser restarts.
* **Multi-Threaded Execution**: Isolates visual feedback frame rendering from Playwright browser DOM operations to guarantee low latency.

---

## System Requirements & Prerequisites

* **Operating System**: Windows 10/11, macOS, or Linux
* **Python Runtime**: Python 3.12 (Recommended)
* **Camera**: Standard USB Webcam or integrated laptop camera
* **Browser Runtime**: Chromium (Managed by Playwright)

---

## Installation & Setup

### 1. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate

```

### 2. Install Required Dependencies

```bash
pip install "numpy<2.0.0" "mediapipe==0.10.14" opencv-python pyautogui playwright

```

### 3. Install Playwright Web Drivers

```bash
playwright install chromium

```

---

## Cookie Configuration & Storage Format

The system persists user login sessions directly to a local JSON file.

* **Default Path**: `D:\Jomnes\aunda\data.json`

### JSON Schema Breakdown

```json
{
  "tiktok": [
    {
      "name": "sessionid",
      "value": "YOUR_TIKTOK_SESSION_ID",
      "domain": ".tiktok.com",
      "hostOnly": false,
      "path": "/",
      "secure": true,
      "httpOnly": true,
      "sameSite": null,
      "session": false,
      "firstPartyDomain": "",
      "partitionKey": null,
      "expirationDate": 1801057719.042,
      "storeId": null
    }
  ],
  "youtube": [
    {
      "name": "SID",
      "value": "YOUR_YOUTUBE_SID",
      "domain": ".youtube.com",
      "hostOnly": false,
      "path": "/",
      "secure": false,
      "httpOnly": false,
      "sameSite": null,
      "session": false,
      "firstPartyDomain": "",
      "partitionKey": null,
      "expirationDate": 1819850381.642,
      "storeId": null
    }
  ]
}

```

---

## System Operational Mechanics: Lock vs Unlock States

```
                 +-----------------------------------+
                 |           UNLOCKED STATE          |
                 | - Free zone switching             |
                 | - Tracking active on wrist/hand   |
                 +-----------------------------------+
                                   |
                  Form Closed Fist | Form Closed Fist
                  in Target Zone   | while Locked
                                   v
                 +-----------------------------------+
                 |            LOCKED STATE           |
                 | - Confined to specific zone       |
                 | - Zone actions fully executable   |
                 +-----------------------------------+

```

1. **UNLOCKED STATE**:
* The system tracks hand center position across zones.
* Actions within individual zones are disabled to prevent accidental clicks or scrolls while moving the hand.
* Transitioning between zones dynamically highlights the targeted zone on the OpenCV display frame.


2. **LOCKED STATE**:
* Initiated by forming a **Closed Fist** inside a targeted zone.
* Locks all inputs to that zone's specific functional handler.
* Visual indicator shifts to locked mode on screen.
* Disables zone switching until an explicit unlock gesture (Closed Fist or Index-Thumb Pinch) is registered.



---

## Comprehensive Zone Logic & Gesture Details

### 1. TOP ZONE: Mouse Cursor & Precision Pointing

#### Main Purpose

Maps hand movement directly to system mouse coordinates and provides left-click capabilities for general web interactions.

#### Primary Landmarks

* **Index Fingertip** (Landmark ID: 8)
* **Middle Fingertip** (Landmark ID: 12)
* **Thumb Tip** (Landmark ID: 4)

#### Detailed Conditions & Rules

* **Zone Entry & Lock**: Position hand in the top third of the viewport and close hand into a **Closed Fist**.
* **Pointer Tracking**: Tracks Index Fingertip (Landmark 8). Converts normalized coordinates (0.0 to 1.0) into primary display pixel resolution.
* **Smoothing Formula**: Uses Exponential Moving Average (EMA):

$$x_{\text{smooth}} = \alpha \cdot x_{\text{raw}} + (1 - \alpha) \cdot x_{\text{prev}}$$



Where $\alpha$ (Alpha) controls responsiveness versus jitter reduction.
* **Left Mouse Click**: Pinch **Index Fingertip** (Landmark 8) and **Middle Fingertip** (Landmark 12) together below a Euclidean distance threshold of 0.04 normalized units.
* **Unlock Condition**: Form a **Closed Fist** or perform an **Index-Thumb Pinch**.

---

### 2. MIDDLE ZONE: Media Feed Scrolling (TikTok & YouTube Shorts)

#### Main Purpose

Delivers vertical scroll inputs tailored for short-form video feeds like TikTok and YouTube Shorts.

#### Primary Landmarks

* **Index Fingertip** (Landmark ID: 8)
* **Middle Fingertip** (Landmark ID: 12)
* **Wrist Point** (Landmark ID: 0)

#### Detailed Conditions & Rules

* **Zone Entry & Lock**: Position hand in the central horizontal region of the frame and form a **Closed Fist**.
* **Scroll Trigger Pose**: Extend **Index and Middle Fingers** upward while keeping Ring and Pinky folded down (**Two-Finger Vertical Pose**).
* **Scroll Up Execution**: Move extended hand upward along the camera Y-axis. Triggers Playwright page scroll up or simulates `Up Arrow` key press for YouTube Shorts / TikTok previous video.
* **Scroll Down Execution**: Move extended hand downward along the Y-axis. Triggers Playwright page scroll down or simulates `Down Arrow` key press for YouTube Shorts / TikTok next video.
* **Invert Scroll Vector**: Perform an **Index-Thumb Pinch** to switch scroll direction logic (Normal vs Inverted).
* **Unlock Condition**: Form a **Closed Fist**.

---

### 3. BOTTOM ZONE: Navigation Menu & Cookie Manager

#### Main Purpose

Interactive menu overlay allowing real-time URL switching between YouTube and TikTok, plus explicit trigger points for cookie persistence.

#### Sub-Menu Items

1. `1: YOUTUBE` -> Navigates Playwright instance to `https://www.youtube.com`
2. `2: TIKTOK` -> Navigates Playwright instance to `https://www.tiktok.com`
3. `3: SAVE COOKIE` -> Serializes current context from cookie editor extension into `data.json`
4. `4: PT4` -> Reserved action hook
5. `5: CANCEL` -> Exits menu without executing actions

#### Detailed Conditions & Rules

* **Zone Entry & Lock**: Move hand to the lower third of the screen frame and form a **Closed Fist**.
* **Cycle Options**: Perform an **Index-Thumb Pinch** (Landmark 4 to Landmark 8 contact) to cycle sequentially through items 1 through 5.
* **Confirm Option**: Form a **Closed Fist** to execute the currently highlighted menu choice.
* **Unlock Condition**: Form a **Closed Fist** on option `5: CANCEL` or complete any menu command execution.

---

## Keyboard Control Matrix

| Key Command | Executed Function |
| --- | --- |
| **Q** | Closes OpenCV video feed, shuts down Playwright browser context, and safely exits process. |
| **R** | Clears EMA coordinate history buffer and resets hand tracking system state. |

---

## Acknowledgements

* **Architecture & Code Generation**: Built with AI collaboration for code structuring, MediaPipe pipeline design, and multi-threading logic.
* **Libraries**: OpenCV, MediaPipe, Playwright, PyAutoGUI.

## Running the Application

Launch the main controller script

```bash
python main.py

---
[!NOTE]
**Project Status & Acknowledgements**

Designed, architected, and tested by **Im Boravath**. Code generation, algorithm optimization, and boilerplate implementation were built in collaboration with AI assistance.
 
*Current version (`v0.9.0-beta`) is a proof-of-concept and does not yet fully support automatic cookie/session extraction.*

```

```

```
=======
# Aunda
>>>>>>> 002bc89d471db48c85d68ecdf9ffde3694fca153

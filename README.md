# Aunda: Web DOM Hand Gesture Control System

A real-time hand gesture interaction framework designed to control web browsers and desktop cursor navigation using computer vision and browser automation tools.

---

## Technical Architecture Overview


```

+-----------------------------------------------------------------------+
|                             CAMERA INPUT                              |
|                       (USB / Integrated Webcam)                       |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                          OPENCV CAPTURE LOOP                          |
|               Captures raw frame and flips horizontally               |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                         MEDIAPIPE HANDS ENGINE                        |
|        Extracts 21 3D Hand Landmarks and Normalized Coordinates       |
+-----------------------------------------------------------------------+
|
v
+-----------------------------------------------------------------------+
|                       ZONE & GESTURE DISPATCHER                       |
|               Determines Frame Spatial Location and Pose              |
+-----------------------------------------------------------------------+
|
+-------------------------+-------------------------+
|                         |                         |
v                         v                         v
+-----------------+       +-----------------+       +-----------------+
|    TOP ZONE     |       |   MIDDLE ZONE   |       |   BOTTOM ZONE   |
|  Mouse / Cursor |       | Feed Scrolling  |       | Context Menu    |
+-----------------+       +-----------------+       +-----------------+
|                         |                         |
| Exponential Moving |   | Normalized Y-Axis |     | Sub-Item Selection |
| Average (EMA)      |   | Delta Offset      |     | Processing       |
v                         v                         v
+-----------------+       +-----------------+       +-----------------+
| PyAutoGUI       |       | Playwright DOM  |       | Playwright /    |
| Cursor Control  |       | Mouse Wheel /   |       | Cookie Engine   |
| & Clicks        |       | Keyboard Key    |       | JSON Storage    |
+-----------------+       +-----------------+       +-----------------+

```

---

## Core System Features

* **Exponential Moving Average (EMA) Cursor Smoothing**: Implements a tracking algorithm with deadzone filtering to reduce coordinate jitter during precision cursor tracking.
* **Zone-Based Spatial Interface**: Divides the video frame into three distinct functional zones (TOP, MIDDLE, BOTTOM) to prevent accidental cross-triggering of gestures.
* **State Locking Model**: Uses an explicit closed-fist gesture to switch between Unlocked and Locked states, isolating active operations within a selected zone.
* **Media Feed Control**: Enables vertical feed navigation designed for platforms like TikTok and YouTube Shorts.
* **Session Persistence**: Reads and serializes browser session cookies directly to local JSON storage (`data.json`) to maintain state between executions.
* **Multi-Threaded Execution**: Separates video frame rendering loops from browser automation calls to ensure reliable real-time performance.

---

## Prerequisites and System Requirements

* **Operating System**: Windows 10/11, macOS, or Linux
* **Python Version**: Python 3.12 (Recommended)
* **Hardware**: USB Webcam or integrated optical sensor
* **Supported Browsers**: Chromium (Automated via Playwright)

---

## Installation and Setup

### 1. Configure Virtual Environment

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

### 2. Install Dependencies

```bash
pip install "numpy<2.0.0" "mediapipe==0.10.14" opencv-python pyautogui playwright

```

### 3. Install Playwright Web Drivers

```bash
playwright install chromium

```

---

## Cookie Configuration Schema

The system loads and serializes session authentication tokens using a localized JSON data structure.

**Path**: `data.json`

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

## State Machine Mechanics

```
                 +-----------------------------------+
                 |          UNLOCKED STATE           |
                 | - Free spatial zone selection     |
                 | - Tracking hand centroid location |
                 +-----------------------------------+
                                   |
                  Form Closed Fist | Form Closed Fist
                  in Target Zone   | while Locked
                                   v
                 +-----------------------------------+
                 |           LOCKED STATE            |
                 | - Confined to selected zone       |
                 | - Zone actions executable         |
                 +-----------------------------------+

```

### Unlocked State

* Tracks hand movement across all zones without executing zone-specific actions.
* Prevents unintentional mouse clicks or scroll events during transitional movements.
* Visual indicators dynamically highlight the candidate zone on the video overlay.

### Locked State

* Activated by forming a **Closed Fist** within a designated zone.
* Binds input parsing strictly to the selected zone handler.
* Disables zone switching until an explicit unlock gesture (**Closed Fist** or **Index-Thumb Pinch**) is recorded.

---

## Zone Operations and Gesture Details

### 1. TOP ZONE: Mouse Cursor & Precision Pointing

#### Purpose

Maps hand coordinates to desktop monitor coordinates and executes primary mouse clicks.

#### Tracked Landmarks

* **Index Fingertip**: Landmark ID 8
* **Middle Fingertip**: Landmark ID 12
* **Thumb Tip**: Landmark ID 4

#### Rules

* **Lock Gesture**: Position hand in the upper section and form a **Closed Fist**.
* **Coordinate Mapping**: Tracks Landmark 8 and maps normalized coordinates $(0.0 - 1.0)$ to absolute display pixels.
* **Coordinate Smoothing Formula**:

$$x_{\text{smooth}} = \alpha \cdot x_{\text{raw}} + (1 - \alpha) \cdot x_{\text{prev}}$$

* **Left Click**: Pinch **Index Fingertip** (Landmark 8) and **Middle Fingertip** (Landmark 12) below a distance threshold of $0.04$ normalized units.
* **Unlock**: Form a **Closed Fist** or execute an **Index-Thumb Pinch**.

---

### 2. MIDDLE ZONE: Media Feed Navigation

#### Purpose

Generates vertical scrolling events for short-form media platforms (TikTok and YouTube Shorts).

#### Tracked Landmarks

* **Index Fingertip**: Landmark ID 8
* **Middle Fingertip**: Landmark ID 12
* **Wrist Point**: Landmark ID 0

#### Rules

* **Lock Gesture**: Position hand in the center region and form a **Closed Fist**.
* **Scroll Pose**: Extend Index and Middle fingers vertically (**Two-Finger Pose**).
* **Scroll Up**: Move extended hand upward along the Y-axis (Triggers previous item / `Up Arrow`).
* **Scroll Down**: Move extended hand downward along the Y-axis (Triggers next item / `Down Arrow`).
* **Invert Scroll Vector**: Perform an **Index-Thumb Pinch** to reverse directional tracking.
* **Unlock**: Form a **Closed Fist**.

---

### 3. BOTTOM ZONE: Navigation & Storage Management

#### Purpose

Provides an interactive menu for switching URLs and triggering cookie serialization routines.

#### Menu Options

1. `1: YOUTUBE` -> Navigates browser to `https://www.youtube.com`
2. `2: TIKTOK` -> Navigates browser to `https://www.tiktok.com`
3. `3: SAVE COOKIE` -> Serializes browser context cookies to `data.json`
4. `4: PT4` -> Unassigned hook
5. `5: CANCEL` -> Exits menu structure

#### Rules

* **Lock Gesture**: Move hand to the bottom third of the frame and form a **Closed Fist**.
* **Cycle Option**: Perform an **Index-Thumb Pinch** to advance through menu options.
* **Confirm Selection**: Form a **Closed Fist** to execute the targeted option.
* **Unlock**: Confirm `5: CANCEL` or complete a menu action.

---

## Keyboard Reference

| Key | Execution Command |
| --- | --- |
| **Q** | Terminates OpenCV capture loop, closes Playwright browser instance, and exits. |
| **R** | Clears EMA coordinate buffers and resets tracking states. |

---

## Running the Application

Execute the primary runtime script:

```bash
python aunda.py

```

---

## Project Status and Acknowledgements

* **System Design & Architecture**: Im Boravath
* **Implementation & Optimization**: Built using AI-assisted pair-programming for boilerplate generation, MediaPipe pipeline structuring, and multithreading implementation.
* **Project Version**: `v0.9.0-beta` (Proof of Concept)

> **Note**: *Automatic extraction and authorization of cookie/session objects are under development and may require manual configuration.*

```

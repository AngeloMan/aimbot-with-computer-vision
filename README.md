# AI aimbot based on Lunar 
**Neural Network Aim Assist** — computer vision academic project using YOLOv5 and PyTorch.

---

## About

Lunar is a neural network-based aim assist system that uses real-time object detection to identify players on screen. The project was developed for educational purposes, demonstrating the application of computer vision in gaming environments.

Detection is based on the [YOLOv5](https://github.com/ultralytics/yolov5) architecture with CUDA acceleration for NVIDIA GPUs. The project does not interfere with other processes' memory — all logic operates through screen capture and hardware-level input simulation.

---

## Features

### Aimbot
- Real-time player detection via YOLOv5 neural network
- Automatic target selection (closest to crosshair within FOV)
- **Aim Bone** — target point: Head, Neck, Chest or Pelvis
- **Strength** — controls snap aggressiveness (1–100%)
- **FOV** — detection radius around the crosshair (50–500px)
- **Auto-Aim** — activates without needing to hold a key
- **Target Prediction** — ready for future position extrapolation
- Configurable keybind via visual menu
- Dedicated mouse movement thread (does not block screen capture)

### Triggerbot
Three activation modes:

| Mode | Behavior |
|---|---|
| **Toggle** | Press key once to enable, press again to disable |
| **Hold** | Active only while the key is held down |
| **Auto-Tap** | First shot after Trigger Delay; subsequent shots every Tap Interval |

- **Trigger Delay** — wait time before the first shot (0–500ms)
- **Tap Interval** — interval between shots in Auto-Tap mode (10–10000ms)
- 150ms grace period to prevent false resets from detection flickering

### Sensitivity (config.json)
- **X/Y Sensitivity** — must match in-game sensitivity settings
- **Targeting Sensitivity** — must match in-game targeting/scoping sensitivity
- `xy_scale` and `targeting_scale` are calculated automatically and saved in real time

---

## Architecture

```
menu.py                  ← Visual configuration interface (tkinter)
lunar.py                 ← Entry point; starts aimbot and keyboard listener
lib/
├── aimbot.py            ← System core
│   ├── MouseThread      ← Mouse movement thread (Queue maxsize=1)
│   ├── TriggerbotThread ← Triggerbot thread (Toggle / Hold / Auto-Tap)
│   └── SettingsWatcher  ← Watches settings.json for live changes
└── config/
    ├── config.json      ← Mouse sensitivity (set via menu)
    └── settings.json    ← All menu settings
```

### Detection Pipeline

```
Screen Capture (mss)
    → YOLOv5 custom model (best.pt)
        → FOV filter
            → Closest target to crosshair selected
                → Aim bone position calculated
                    → MouseThread.update_target(x, y)
```

### Threading Model

| Thread | Rate | Responsibility |
|---|---|---|
| Main loop | Max FPS | Screen capture + YOLO inference + rendering |
| MouseThread | ~250Hz | Smooth mouse movement via SendInput |
| TriggerbotThread | ~250Hz | Manages all three trigger modes |
| SettingsWatcher | ~2Hz | Reloads settings.json when changed |

**MouseThread** uses `Queue(maxsize=1)` — if a newer target arrives mid-movement, the current movement is immediately abandoned, keeping the crosshair responsive on moving targets.

---

## Requirements

- Windows 10/11
- Python 3.10
- NVIDIA GPU with CUDA support (recommended)
- `lib/best.pt` (trained model file)

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/AngeloMan/aimbot-with-computer-vision
cd aimbot-with-computer-vision
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add the model**

Place the `best.pt` file at `lib/best.pt`.

The model can be obtained from the original [zeyad-mansour/Lunar](https://github.com/zeyad-mansour/Lunar) releases, or trained with a custom dataset using YOLOv5.

---

## Usage

**Open the configuration menu:**
```bash
python menu.py
```

Configure the desired options and click **SAVE & LAUNCH** to start.

**Start directly (without menu):**
```bash
python lunar.py
```

**Recollect training data:**
```bash
python lunar.py collect_data
```

### In-game Controls

| Key | Action |
|---|---|
| F2 | Exit and return to menu |
| 0 | Close the visualization window |

---

## Sensitivity Configuration

The `config.json` stores four values:

```json
{"xy_sens": 13.0, "targeting_sens": 100.0, "xy_scale": 1, "targeting_scale": 1}
```

| Field | Description |
|---|---|
| `xy_sens` | X/Y sensitivity from in-game settings |
| `targeting_sens` | Targeting/scoping sensitivity from in-game settings |
| `xy_scale` | Calculated: `10 / xy_sens` |
| `targeting_scale` | Calculated: `1000 / (targeting_sens × xy_sens)` |

`targeting_scale` directly controls how many pixels the mouse moves per unit of distance to the target. If this value is wrong, the aimbot will overshoot or undershoot. Always use the exact values from your in-game settings.

---

## Training a Custom Model

To train a model for a specific game:

**1. Get a dataset**

Browse [Roboflow Universe](https://universe.roboflow.com/) for player detection datasets (e.g. "fortnite player detection", "cs2 player detection").

**2. Train with YOLOv5**
```bash
git clone https://github.com/ultralytics/yolov5
cd yolov5
pip install -r requirements.txt
python train.py --data dataset.yaml --weights yolov5s.pt --epochs 100
```

**3. Use the trained model**
```
runs/train/exp/weights/best.pt  →  copy to  lib/best.pt
```

---

## Known Issues

- `SendInput` mouse movement can lag behind fast-moving targets. Increasing `pixel_increment` in `aimbot.py` reduces the number of calls and improves responsiveness.
- False positives may occur under specific in-game lighting conditions.
- **Auto-Tap** mode depends on `lock_flag`, which requires the target to be within 5px of the crosshair center. A 150ms grace period prevents unnecessary resets on briefly lost targets.

---

## Settings Reference

**settings.json** (generated by menu):
```json
{
  "aimbot": {
    "enabled": true,
    "aim_bone": "Head",
    "strength": 50,
    "fov": 150,
    "auto_aim": false,
    "target_prediction": false,
    "keybind": "RMB"
  },
  "triggerbot": {
    "enabled": false,
    "mode": "Toggle",
    "trigger_delay": 50,
    "tap_interval": 100,
    "keybind": "RMB"
  }
}
```

---

## Tech Stack

| Library | Purpose |
|---|---|
| `torch` + `YOLOv5` | Real-time object detection |
| `mss` | Screen capture via DXGI (high performance) |
| `opencv-python` | Visualization and bounding box rendering |
| `ctypes` + `win32api` | Hardware-level mouse input via SendInput |
| `tkinter` | Visual configuration menu |
| `threading` + `queue` | Parallel processing across threads |
| `pynput` | Global keyboard listener |

---

## License

Distributed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

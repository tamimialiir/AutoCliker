# Auto Clicker

A simple and lightweight Auto Clicker with a modern dark GUI, built with Python and Tkinter.

## Features

- Set custom click coordinates by clicking anywhere on the screen
- Adjustable hold duration (how long the mouse button stays pressed)
- Adjustable interval between clicks
- Finite or Infinite clicking mode
- Hotkey (`S`) to quickly stop clicking
- Clean and modern dark theme interface

## Requirements

- Python 3.8 or higher
- `pynput` library

## Installation

1. Clone the repository or download the files.
2. Install the required package:

```bash
pip install -r requirements.txt
```

## How to Run

```bash
python auto_clicker.py
```

## How to Use

Click the Set Coordinates button, then left-click anywhere on the screen to set the target position.
Adjust the following settings as needed:
Hold Duration (ms): How long each click is held
Interval Between Clicks (ms): Delay between each click
Number of Clicks: Total number of clicks (or enable Infinite)

Press the Start button to begin clicking.
Press the S key on your keyboard or click the Stop button to stop.

### Notes

If the clicks don't work on some applications, try running the program as Administrator.
Use this tool responsibly and only on applications/games that allow automation.
The coordinate system is based on your screen resolution.

### License
This project is open source and available under the MIT License.
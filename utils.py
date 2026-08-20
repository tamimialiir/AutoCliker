import sys
import os
from pynput.keyboard import Key, KeyCode

SPECIAL_KEYS = {
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    "space": Key.space, "enter": Key.enter, "tab": Key.tab,
    "esc": Key.esc, "backspace": Key.backspace, "delete": Key.delete,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "home": Key.home, "end": Key.end, "page_up": Key.page_up, "page_down": Key.page_down,
    "shift": Key.shift, "ctrl": Key.ctrl, "alt": Key.alt,
    "cmd": Key.cmd, "caps_lock": Key.caps_lock,
}

MODIFIER_NAME = {
    Key.ctrl: "ctrl", Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
    Key.alt: "alt", Key.alt_l: "alt", Key.alt_r: "alt",
    Key.shift: "shift", Key.shift_l: "shift", Key.shift_r: "shift",
    Key.cmd: "cmd", Key.cmd_l: "cmd", Key.cmd_r: "cmd",
}

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Shifted symbol -> base key (US layout)
SHIFT_SYMBOL_TO_BASE = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
    ":": ";", "\"": "'", "<": ",", ">": ".", "?": "/",
    "~": "`",
}

def key_to_str(key, held_mods=None):
    """
    Convert pynput key to a stable physical-ish string.
    held_mods: optional set of modifier names currently held (for unshifting).
    """
    held_mods = held_mods or set()

    if key in MODIFIER_NAME:
        return MODIFIER_NAME[key]

    if isinstance(key, Key):
        return str(key).replace("Key.", "").lower()

    if isinstance(key, KeyCode):
        vk = getattr(key, "vk", None)

        # Prefer virtual-key for letters and digits (immune to Ctrl/Shift char distortion)
        if vk is not None:
            # A-Z
            if 65 <= vk <= 90:
                return chr(vk).lower()
            # Top-row 0-9
            if 48 <= vk <= 57:
                return chr(vk)
            # Numpad 0-9 (Windows)
            if 96 <= vk <= 105:
                return str(vk - 96)

        ch = key.char
        if ch is not None:
            code = ord(ch)
            # Ctrl+A .. Ctrl+Z produce codes 1..26
            if 1 <= code <= 26:
                return chr(ord("a") + code - 1)
            if ch.isprintable():
                # If Shift is held and we got a shifted symbol, map back to base key
                if "shift" in held_mods and ch in SHIFT_SYMBOL_TO_BASE:
                    return SHIFT_SYMBOL_TO_BASE[ch]
                return ch.lower()

        if vk is not None:
            return f"vk_{vk}"

    return str(key).lower()

def str_to_key(s):
    s = s.lower().strip()
    if s in SPECIAL_KEYS:
        return SPECIAL_KEYS[s]
    if len(s) == 1:
        return s
    return s

def parse_key_combo(combo):
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if not parts:
        return [], "a"
    mod_order = ["ctrl", "alt", "shift", "cmd"]
    modifiers = []
    main = parts[-1]
    for p in parts[:-1]:
        if p in mod_order and p in SPECIAL_KEYS:
            modifiers.append(SPECIAL_KEYS[p])
    return modifiers, main

# Colors for action types in the points list (Catppuccin-inspired)
ACTION_COLORS = {
    "click":  "#a6e3a1",  # green
    "drag":   "#89b4fa",  # blue
    "scroll": "#cba6f7",  # purple
    "wait":   "#f9e2af",  # yellow
    "key":    "#fab387",  # peach / orange
}

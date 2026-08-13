import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import random
import platform
import ctypes
import copy
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, KeyCode, Listener as KeyboardListener, Controller as KeyboardController


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


class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)
        self.version = "v5.0"
        
        try:
            icon_path = resource_path("icon.png")
            self._app_icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass
            
        self.points = []
        self.selected_index = None
        self.is_running = False
        self.is_paused = False
        self.stop_flag = False
        self.is_recording = False
        self.clipboard_point = None
        self.current_cycle = 0
        self.current_step_index = 0

        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.p_hotkey_enabled = tk.BooleanVar(value=True)
        self.rs_hotkey_enabled = tk.BooleanVar(value=True)
        self.re_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)

        self.start_hotkey = "f1"
        self.pause_hotkey = "f2"
        self.stop_hotkey = "f3"
        self.record_start_hotkey = "f4"
        self.record_stop_hotkey = "f5"

        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.click_listener = None
        self.keyboard_listener = None
        self.record_mouse_listener = None
        self.record_keyboard_listener = None

        self.waiting_for_hotkey = None
        self.adding_mode = None
        self.temp_drag_start = None
        self.record_events = []
        self.record_start_time = 0

        self.drag_start_index = None
        self.drag_current_index = None
        self.preview_windows = []

        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())
        self.setup_ui()
        self.bind_list_shortcuts()
        self.start_keyboard_listener()
        self.root.update_idletasks()
        width = 540
        height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = ((screen_height - height) // 2) - 30
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def force_english_keyboard(self):
        if platform.system() == "Windows":
            try:
                ctypes.windll.user32.LoadKeyboardLayoutW("00000409", 1)
            except Exception:
                pass

    def is_focus_on_input(self):
        focused = self.root.focus_get()
        if focused is None:
            return False
        return focused.winfo_class() in ("TEntry", "TSpinbox", "Entry", "Spinbox")

    def is_busy(self):
        """True when actively running (not paused) or recording — blocks list edits."""
        return self.is_recording or (self.is_running and not self.is_paused)

    def validate_number(self, action, value_if_allowed):
        if action == "1":
            return value_if_allowed.isdigit() or value_if_allowed == ""
        return True

    def select_index(self, index):
        if not self.points:
            self.selected_index = None
            self.edit_btn.config(state="disabled")
            self.points_listbox.selection_clear(0, tk.END)
            return
        index = max(0, min(index, len(self.points) - 1))
        self.selected_index = index
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(index)
        self.points_listbox.activate(index)
        self.points_listbox.see(index)
        self.edit_btn.config(state="normal")

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground="#313244", background="#313244",
                        foreground="#cdd6f4", arrowcolor="#cdd6f4",
                        bordercolor="#45475a", darkcolor="#313244", lightcolor="#313244",
                        selectbackground="#313244", selectforeground="#cdd6f4")
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#313244"), ("!disabled", "#313244")],
                  foreground=[("readonly", "#cdd6f4"), ("!disabled", "#cdd6f4")],
                  selectbackground=[("readonly", "#313244")],
                  selectforeground=[("readonly", "#cdd6f4")])
        style.configure("TButton", padding=3, font=("Segoe UI", 9))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 9))
        style.configure("TSpinbox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TLabelframe", background="#1e1e2e", foreground="#89b4fa")
        style.configure("TLabelframe.Label", background="#1e1e2e", foreground="#89b4fa", font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("Hotkey.TButton", padding=2, font=("Segoe UI", 6))
        style.configure("Hotkey.TCheckbutton", background="#313244", foreground="#cdd6f4", font=("Segoe UI", 7))

        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 15, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(6, 3))

        points_frame = ttk.LabelFrame(self.root, text=" Points Sequence", padding=5)
        points_frame.pack(fill="x", padx=10, pady=2)

        list_frame = tk.Frame(points_frame, bg="#1e1e2e")
        list_frame.pack(fill="x")
        self.points_listbox = tk.Listbox(list_frame, height=7, bg="#313244", fg="#cdd6f4",
                                         selectbackground="#89b4fa", font=("Consolas", 9),
                                         relief="flat", highlightthickness=0)
        self.points_listbox.pack(side="left", fill="x", expand=True)
        self.points_listbox.bind("<<ListboxSelect>>", self.on_point_select)
        self.points_listbox.bind("<Double-Button-1>", lambda e: self.open_edit_popup())
        self.points_listbox.bind("<ButtonPress-1>", self.on_list_drag_start)
        self.points_listbox.bind("<B1-Motion>", self.on_list_drag_motion)
        self.points_listbox.bind("<ButtonRelease-1>", self.on_list_drag_drop)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.points_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.points_listbox.config(yscrollcommand=scrollbar.set)

        btn_row = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="Add Click", command=lambda: self.start_add_point("click")).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(btn_row, text="Add Drag", command=lambda: self.start_add_point("drag")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="Add Scroll", command=self.start_add_scroll).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="Add Key", command=self.add_key_action).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="Add Wait", command=self.add_wait).pack(side="left", expand=True, fill="x", padx=(2, 0))

        btn_row2 = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row2.pack(fill="x", pady=(3, 0))

        rec_frame = tk.Frame(btn_row2, bg="#1e1e2e")
        rec_frame.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.record_indicator = tk.Canvas(rec_frame, width=14, height=14, bg="#1e1e2e",
                                          highlightthickness=0, bd=0)
        self.record_indicator.pack(side="left", padx=(0, 4))
        self.record_indicator.create_oval(2, 2, 12, 12, fill="#5c1a1a", outline="", tags="dot")
        self.record_btn = ttk.Button(rec_frame, text="Record", command=self.toggle_recording)
        self.record_btn.pack(side="left", expand=True, fill="x")

        self.edit_btn = ttk.Button(btn_row2, text="Edit", command=self.open_edit_popup, state="disabled")
        self.edit_btn.pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row2, text="↑", width=3, command=self.move_up).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="↓", width=3, command=self.move_down).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Remove", command=self.remove_point).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row2, text="Clear", command=self.clear_points).pack(side="left", expand=True, fill="x", padx=(2, 0))

        global_frame = ttk.LabelFrame(self.root, text=" Global Settings ", padding=8)
        global_frame.pack(fill="x", padx=10, pady=2)

        # Speed control row (top of Global Settings)
        speed_row = tk.Frame(global_frame, bg="#1e1e2e")
        speed_row.pack(fill="x", pady=(0, 6))
        speed_box = tk.Frame(speed_row, bg="#313244", padx=8, pady=6)
        speed_box.pack(fill="x", expand=True)
        sp = tk.Frame(speed_box, bg="#313244")
        sp.pack(fill="x")
        tk.Label(sp, text="⚡  Speed", bg="#313244", fg="#a6adc8", font=("Segoe UI", 8)).pack(side="left")
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(
            sp, from_=0.1, to=20.0, resolution=0.1, orient="horizontal",
            variable=self.speed_var, length=220, showvalue=0,
            bg="#313244", fg="#cdd6f4", troughcolor="#45475a",
            highlightthickness=0, activebackground="#89b4fa",
            command=self._on_speed_change
        )
        self.speed_scale.pack(side="left", padx=(10, 6), fill="x", expand=True)
        self.speed_value_label = tk.Label(sp, text="x1.0", bg="#313244", fg="#89b4fa",
                                          font=("Segoe UI", 9, "bold"), width=6, anchor="w")
        self.speed_value_label.pack(side="left")
        self.speed_reset_btn = ttk.Button(sp, text="Reset", width=6,
                                          style="Hotkey.TButton",
                                          command=self.reset_speed)
        self.speed_reset_btn.pack(side="left", padx=(4, 0))

        g_row1 = tk.Frame(global_frame, bg="#1e1e2e")
        g_row1.pack(fill="x", pady=(0, 4))

        rand_box = tk.Frame(g_row1, bg="#313244", padx=8, pady=6)
        rand_box.pack(side="left", fill="x", expand=True, padx=(0, 4))
        rt = tk.Frame(rand_box, bg="#313244")
        rt.pack(fill="x")
        tk.Label(rt, text="⏱  Time Jitter", bg="#313244", fg="#a6adc8", font=("Segoe UI", 8)).pack(side="left")
        self.random_var = tk.IntVar(value=0)
        ttk.Spinbox(rt, from_=0, to=500, textvariable=self.random_var, width=5,
                    validate="key", validatecommand=vcmd).pack(side="left", padx=(8, 0))
        tk.Label(rt, text="±ms", bg="#313244", fg="#6c7086", font=("Segoe UI", 8)).pack(side="left", padx=(2, 0))

        pos_box = tk.Frame(g_row1, bg="#313244", padx=8, pady=6)
        pos_box.pack(side="left", fill="x", expand=True, padx=(4, 0))
        rp = tk.Frame(pos_box, bg="#313244")
        rp.pack(fill="x")
        tk.Label(rp, text="🎯  Pos. Jitter", bg="#313244", fg="#a6adc8", font=("Segoe UI", 8)).pack(side="left")
        self.pos_random_var = tk.IntVar(value=0)
        ttk.Spinbox(rp, from_=0, to=50, textvariable=self.pos_random_var, width=5,
                    validate="key", validatecommand=vcmd).pack(side="left", padx=(8, 0))
        tk.Label(rp, text="±px", bg="#313244", fg="#6c7086", font=("Segoe UI", 8)).pack(side="left", padx=(2, 0))

        g_row2 = tk.Frame(global_frame, bg="#1e1e2e")
        g_row2.pack(fill="x")

        cyc_box = tk.Frame(g_row2, bg="#313244", padx=8, pady=6)
        cyc_box.pack(side="left", fill="x", expand=True, padx=(0, 4))
        cy = tk.Frame(cyc_box, bg="#313244")
        cy.pack(fill="x")
        tk.Label(cy, text="🔄  Cycles", bg="#313244", fg="#a6adc8", font=("Segoe UI", 8)).pack(side="left")
        self.rep_var = tk.IntVar(value=1)
        self.rep_spin = ttk.Spinbox(cy, from_=1, to=99999, textvariable=self.rep_var, width=5,
                                    validate="key", validatecommand=vcmd)
        self.rep_spin.pack(side="left", padx=(8, 0))
        ttk.Checkbutton(cy, text="Infinite", variable=self.infinite,
                        command=self.toggle_infinite).pack(side="left", padx=(10, 0))

        opt_box = tk.Frame(g_row2, bg="#313244", padx=8, pady=6)
        opt_box.pack(side="left", fill="both", expand=True, padx=(4, 0))
        op = tk.Frame(opt_box, bg="#313244")
        op.pack(fill="x")
        tk.Label(op, text="⚙  Options ", bg="#313244", fg="#a6adc8", font=("Segoe UI", 8)).pack(side="left")
        ttk.Checkbutton(op, text="Always on Top", variable=self.always_on_top,
                        command=self.toggle_topmost).pack(side="left", padx=(10, 0))

        hotkey_frame = ttk.LabelFrame(self.root, text=" Hotkeys ", padding=8)
        hotkey_frame.pack(fill="x", padx=10, pady=2)

        def make_hk_box(parent, label_attr, text, which, enabled_var, padx_cfg):
            box = tk.Frame(parent, bg="#313244", padx=8, pady=5)
            box.pack(side="left", fill="x", expand=True, **padx_cfg)
            inner = tk.Frame(box, bg="#313244")
            inner.pack(fill="x")
            lbl = tk.Label(inner, text=text, bg="#313244", fg="#cdd6f4",
                           font=("Segoe UI", 8), anchor="w")
            lbl.pack(side="left")
            setattr(self, label_attr, lbl)
            ttk.Button(inner, text="Change", width=7,
                       style="Hotkey.TButton",
                       command=lambda w=which: self.change_hotkey(w)).pack(side="right", padx=(4, 0))
            ttk.Checkbutton(inner, text="On", variable=enabled_var,
                            style="Hotkey.TCheckbutton").pack(side="right")
            return box

        hk_row1 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk_row1.pack(fill="x", pady=(0, 4))
        make_hk_box(hk_row1, "start_hk_label",
                    f"▶ Start: {self.start_hotkey.upper()}", "start",
                    self.g_hotkey_enabled, {"padx": (0, 2)})
        make_hk_box(hk_row1, "pause_hk_label",
                    f"⏸ Pause: {self.pause_hotkey.upper()}", "pause",
                    self.p_hotkey_enabled, {"padx": (2, 2)})
        make_hk_box(hk_row1, "stop_hk_label",
                    f"⏹ Stop: {self.stop_hotkey.upper()}", "stop",
                    self.s_hotkey_enabled, {"padx": (2, 0)})

        hk_row2 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk_row2.pack(fill="x")
        make_hk_box(hk_row2, "record_start_hk_label",
                    f"⏺ Start Rec: {self.record_start_hotkey.upper()}", "record_start",
                    self.rs_hotkey_enabled, {"padx": (0, 2)})
        make_hk_box(hk_row2, "record_stop_hk_label",
                    f"⏹ Stop Rec: {self.record_stop_hotkey.upper()}", "record_stop",
                    self.re_hotkey_enabled, {"padx": (2, 0)})

        profile_frame = tk.Frame(self.root, bg="#1e1e2e")
        profile_frame.pack(fill="x", padx=10, pady=3)
        ttk.Button(profile_frame, text="Save Profile", command=self.save_profile).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(profile_frame, text="Load Profile", command=self.load_profile).pack(side="left", expand=True, fill="x", padx=(3, 0))

        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(fill="x", padx=10, pady=2)
        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.pause_btn = ttk.Button(action_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side="left", expand=True, fill="x", padx=2)
        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=2)
        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x", padx=(2, 0))

        bottom = tk.Frame(self.root, bg="#1e1e2e")
        bottom.pack(fill="x", padx=10, pady=(4, 6))
        self.status_label = tk.Label(bottom, text="Ready", font=("Segoe UI", 9),
                                     bg="#1e1e2e", fg="#f9e2af")
        self.status_label.pack(side="left")
        self.progress_label = tk.Label(bottom, text="", font=("Segoe UI", 8),
                                       bg="#1e1e2e", fg="#a6adc8")
        self.progress_label.pack(side="left", padx=(10, 0))
        tk.Label(bottom, text=self.version, font=("Segoe UI", 8),
                 bg="#1e1e2e", fg="#6c7086").pack(side="right")

    def bind_list_shortcuts(self):
        self.points_listbox.bind("<Delete>", lambda e: self.on_list_delete(e))
        self.root.bind("<Delete>", lambda e: self.on_list_delete(e))
        for mod in ("Control", "Command"):
            self.root.bind(f"<{mod}-c>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-C>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-x>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-X>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-v>", lambda e: self.on_list_paste(e))
            self.root.bind(f"<{mod}-V>", lambda e: self.on_list_paste(e))

    def on_list_delete(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is not None:
            self.remove_point()
            return "break"

    def on_list_copy(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        self.clipboard_point = copy.deepcopy(self.points[self.selected_index])
        self.status_label.config(text="Item copied", fg="#a6e3a1")
        return "break"

    def on_list_cut(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        idx = self.selected_index
        self.clipboard_point = copy.deepcopy(self.points[idx])
        del self.points[idx]
        self.refresh_points_list()
        if self.points:
            self.select_index(min(idx, len(self.points) - 1))
        else:
            self.selected_index = None
            self.edit_btn.config(state="disabled")
        self.status_label.config(text="Item cut", fg="#f9e2af")
        return "break"

    def on_list_paste(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.clipboard_point is None:
            self.status_label.config(text="Clipboard empty", fg="#f38ba8")
            return "break"
        new_item = copy.deepcopy(self.clipboard_point)
        if self.selected_index is not None and 0 <= self.selected_index < len(self.points):
            insert_at = self.selected_index + 1
        else:
            insert_at = len(self.points)
        self.points.insert(insert_at, new_item)
        self.refresh_points_list()
        self.select_index(insert_at)
        self.status_label.config(text="Item pasted", fg="#a6e3a1")
        return "break"

    def _on_speed_change(self, value=None):
        try:
            v = float(self.speed_var.get())
            self.speed_value_label.config(text=f"x{v:.1f}")
        except Exception:
            pass

    def reset_speed(self):
        self.speed_var.set(1.0)
        self._on_speed_change()

    def set_speed_controls_state(self, enabled):
        state = "normal" if enabled else "disabled"
        try:
            self.speed_scale.config(state=state)
            self.speed_reset_btn.config(state=state)
        except Exception:
            pass

    def set_record_indicator(self, active):
        self.record_indicator.itemconfig("dot", fill="#ef4444" if active else "#5c1a1a")

    def on_list_drag_start(self, event):
        if self.is_busy():
            self.drag_start_index = None
            self.drag_current_index = None
            return
        index = self.points_listbox.nearest(event.y)
        if 0 <= index < len(self.points):
            self.drag_start_index = index
            self.drag_current_index = index
            self.points_listbox.selection_clear(0, tk.END)
            self.points_listbox.selection_set(index)
            self.points_listbox.activate(index)

    def on_list_drag_motion(self, event):
        if self.is_busy() or self.drag_start_index is None:
            return
        new_index = self.points_listbox.nearest(event.y)
        if new_index == self.drag_current_index or not (0 <= new_index < len(self.points)):
            return
        item = self.points.pop(self.drag_current_index)
        self.points.insert(new_index, item)
        self.drag_current_index = new_index
        self.refresh_points_list()
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(new_index)
        self.points_listbox.activate(new_index)
        self.points_listbox.see(new_index)

    def on_list_drag_drop(self, event):
        if self.drag_start_index is not None and self.drag_current_index is not None:
            self.selected_index = self.drag_current_index
            self.edit_btn.config(state="normal")
            if self.drag_start_index != self.drag_current_index:
                self.status_label.config(text="Order changed", fg="#a6e3a1")
        self.drag_start_index = None
        self.drag_current_index = None

    def on_point_select(self, event=None):
        if self.is_busy():
            return
        sel = self.points_listbox.curselection()
        if sel:
            self.selected_index = sel[0]
            self.edit_btn.config(state="normal")
        else:
            if self.selected_index is None:
                self.edit_btn.config(state="disabled")

    def highlight_current(self, index):
        try:
            self.points_listbox.selection_clear(0, tk.END)
            if 0 <= index < self.points_listbox.size():
                self.points_listbox.selection_set(index)
                self.points_listbox.activate(index)
                self.points_listbox.see(index)
        except Exception:
            pass

    def clear_highlight(self):
        self.points_listbox.selection_clear(0, tk.END)

    def refresh_points_list(self):
        self.points_listbox.delete(0, tk.END)
        for i, p in enumerate(self.points, 1):
            name = p.get("name", "").strip()
            prefix = f"{i}. "
            if name:
                prefix += f"{name}: "
            action = p.get("action")
            if action == "drag":
                text = f"{prefix}DRAG ({p['x']},{p['y']}) → ({p['drag_x']},{p['drag_y']}) x{p.get('count', 1)}"
            elif action == "wait":
                text = f"{prefix}WAIT {p.get('delay', 500)}ms"
            elif action == "key":
                text = f"{prefix}KEY '{p.get('key', '?')}' x{p.get('count', 1)}"
            elif action == "scroll":
                direction = "UP" if p.get("dy", 0) > 0 else "DOWN"
                text = f"{prefix}SCROLL {direction} ({p.get('x', 0)},{p.get('y', 0)}) x{p.get('count', 1)}"
            else:
                text = f"{prefix}CLICK ({p['x']},{p['y']}) {p.get('type', 'Left')} x{p.get('count', 1)}"
            self.points_listbox.insert(tk.END, text)

    def clear_previews(self):
        for w in self.preview_windows:
            try:
                lst = getattr(w, "_drag_listener", None)
                if lst is not None:
                    try:
                        if lst.is_alive():
                            lst.stop()
                    except Exception:
                        pass
                w.destroy()
            except Exception:
                pass
        self.preview_windows.clear()

    def show_point_preview(self, x, y, color="#f38ba8", label=""):
        try:
            preview = tk.Toplevel(self.root)
            preview.overrideredirect(True)
            preview.attributes("-topmost", True)

            transparent = "#010101"
            try:
                preview.attributes("-transparentcolor", transparent)
            except Exception:
                transparent = "#1e1e2e"

            size = 36
            preview.geometry(f"{size}x{size}+{int(x) - size // 2}+{int(y) - size // 2}")

            canvas = tk.Canvas(preview, width=size, height=size, bg=transparent,
                               highlightthickness=0, bd=0)
            canvas.pack()

            center = size // 2
            outer_margin = 6
            inner_r = 3
            extend = 4
            line_width = 1

            canvas.create_line(outer_margin - extend, center,
                               size - outer_margin + extend, center,
                               fill=color, width=line_width)
            canvas.create_line(center, outer_margin - extend,
                               center, size - outer_margin + extend,
                               fill=color, width=line_width)

            canvas.create_oval(outer_margin, outer_margin,
                               size - outer_margin, size - outer_margin,
                               outline=color, width=2)

            canvas.create_oval(center - inner_r, center - inner_r,
                               center + inner_r, center + inner_r,
                               fill=color, outline="")

            canvas.create_oval(center - 2, center - 2, center + 2, center + 2,
                               fill=transparent, outline="")

            self.preview_windows.append(preview)
            return preview
        except Exception:
            return None

    def _move_preview(self, preview_win, x_var, y_var):
        if preview_win is None:
            return
        try:
            x, y = int(x_var.get()), int(y_var.get())
            size = 36
            preview_win.geometry(f"{size}x{size}+{x - size // 2}+{y - size // 2}")
        except Exception:
            pass

    def make_preview_draggable(self, preview_win, x_var, y_var):
        """
        Drag via global mouse listener with a generous hit radius around the
        marker center. Appearance stays hollow/transparent; the whole disk
        area is still easy to grab.
        """
        if preview_win is None:
            return
        size = 36
        hit_radius = 20  # px from center — covers full outer circle + a bit more
        state = {"dragging": False}

        def marker_center():
            try:
                return int(x_var.get()), int(y_var.get())
            except Exception:
                return None

        def on_click(x, y, button, pressed):
            if button != Button.left:
                return True
            if pressed:
                c = marker_center()
                if c is None:
                    return True
                if (x - c[0]) ** 2 + (y - c[1]) ** 2 <= hit_radius ** 2:
                    state["dragging"] = True
                    try:
                        preview_win.lift()
                    except Exception:
                        pass
            else:
                if state["dragging"]:
                    state["dragging"] = False
                    try:
                        x_var.set(int(x))
                        y_var.set(int(y))
                    except Exception:
                        pass
            return True

        def on_move(x, y):
            if not state["dragging"]:
                return
            try:
                preview_win.geometry(f"{size}x{size}+{x - size // 2}+{y - size // 2}")
                x_var.set(int(x))
                y_var.set(int(y))
            except Exception:
                pass

        listener = mouse.Listener(on_click=on_click, on_move=on_move)
        listener.start()
        preview_win._drag_listener = listener

        def _stop_listener(event=None):
            lst = getattr(preview_win, "_drag_listener", None)
            if lst is not None:
                try:
                    if lst.is_alive():
                        lst.stop()
                except Exception:
                    pass
                preview_win._drag_listener = None

        preview_win.bind("<Destroy>", _stop_listener)

    def open_add_popup(self, action, data):
        """Popup for configuring a newly captured Click or Drag before adding it to the list."""
        self.clear_previews()
        preview_main = preview_end = None
        if action == "click":
            preview_main = self.show_point_preview(data.get("x", 0), data.get("y", 0), "#89b4fa", "C")
        elif action == "drag":
            preview_main = self.show_point_preview(data.get("x", 0), data.get("y", 0), "#a6e3a1", "S")
            preview_end = self.show_point_preview(data.get("drag_x", 0), data.get("drag_y", 0), "#f38ba8", "E")

        popup = tk.Toplevel(self.root)
        popup.title("Add " + ("Click" if action == "click" else "Drag"))
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        # No grab_set: allows dragging the on-screen preview markers

        def on_popup_close():
            self.clear_previews()
            popup.destroy()
            self.status_label.config(text="Add cancelled", fg="#f9e2af")

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        vcmd = (popup.register(self.validate_number), "%d", "%P")

        tk.Label(popup, text="Configure new " + ("Click" if action == "click" else "Drag"),
                 font=("Segoe UI", 11, "bold"), bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 6))
        tk.Label(popup, text="Drag the on-screen marker(s) to reposition",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=15, pady=(0, 6))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value=data.get("name", ""))
        ttk.Entry(name_frame, textvariable=name_var, width=22).pack(side="left", padx=(6, 0))

        frame = tk.Frame(popup, bg="#1e1e2e")
        frame.pack(padx=15, pady=5)
        entries = {}

        def bind_live_preview(var_x, var_y, preview_win):
            if preview_win is None:
                return
            def on_change(*_):
                self._move_preview(preview_win, var_x, var_y)
            var_x.trace_add("write", on_change)
            var_y.trace_add("write", on_change)
            self.make_preview_draggable(preview_win, var_x, var_y)

        if action == "drag":
            labels = [("Start X:", "x"), ("Start Y:", "y"), ("End X:", "drag_x"), ("End Y:", "drag_y"),
                      ("Duration (ms):", "hold"), ("Repeat:", "count"), ("Delay Between Repeats (ms):", "delay_after")]
            for i, (label, key) in enumerate(labels):
                tk.Label(frame, text=label, bg="#1e1e2e", fg="#cdd6f4").grid(row=i, column=0, sticky="w", pady=2)
                var = tk.IntVar(value=data.get(key, 1 if key == "count" else 0))
                max_val = 100 if key == "count" else (99999 if key in ("hold", "delay_after") else 10000)
                from_val = 1 if key == "count" else 0
                ttk.Spinbox(frame, from_=from_val, to=max_val, textvariable=var, width=10,
                            validate="key", validatecommand=vcmd).grid(row=i, column=1, pady=2, padx=5)
                entries[key] = var
            bind_live_preview(entries["x"], entries["y"], preview_main)
            bind_live_preview(entries["drag_x"], entries["drag_y"], preview_end)
        else:
            # click
            tk.Label(frame, text="X:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
            var_x = tk.IntVar(value=data.get("x", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_x, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
            entries["x"] = var_x
            tk.Label(frame, text="Y:", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
            var_y = tk.IntVar(value=data.get("y", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_y, width=10,
                        validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)
            entries["y"] = var_y
            bind_live_preview(var_x, var_y, preview_main)
            tk.Label(frame, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            var_hold = tk.IntVar(value=data.get("hold", 50))
            hold_spin = ttk.Spinbox(frame, from_=10, to=2000, textvariable=var_hold, width=10,
                                    validate="key", validatecommand=vcmd)
            hold_spin.grid(row=2, column=1, pady=2, padx=5)
            entries["hold"] = var_hold
            tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
            var_count = tk.IntVar(value=data.get("count", 1))
            ttk.Spinbox(frame, from_=1, to=100, textvariable=var_count, width=10,
                        validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
            entries["count"] = var_count
            tk.Label(frame, text="Type:", bg="#1e1e2e", fg="#cdd6f4").grid(row=4, column=0, sticky="w", pady=2)
            var_type = tk.StringVar(value=data.get("type", "Left"))
            type_combo = ttk.Combobox(frame, textvariable=var_type,
                                      values=["Left", "Right", "Double", "Middle"],
                                      state="readonly", width=8)
            type_combo.grid(row=4, column=1, pady=2, padx=5)
            type_combo.set(data.get("type", "Left"))
            entries["type"] = var_type

            def on_type_change(event=None):
                hold_spin.config(state="disabled" if var_type.get() == "Double" else "normal")
            type_combo.bind("<<ComboboxSelected>>", on_type_change)
            on_type_change()
            tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=data.get("delay_after", 100))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        def apply_add():
            try:
                new_p = {"action": action, "name": name_var.get().strip()}
                if action == "drag":
                    for key in ["x", "y", "drag_x", "drag_y", "hold", "count", "delay_after"]:
                        new_p[key] = int(entries[key].get())
                    new_p["type"] = "Left"
                else:
                    new_p["x"] = int(entries["x"].get())
                    new_p["y"] = int(entries["y"].get())
                    new_p["hold"] = int(entries["hold"].get())
                    new_p["count"] = int(entries["count"].get())
                    new_p["type"] = entries["type"].get()
                    new_p["delay_after"] = int(entries["delay_after"].get())
                self.points.append(new_p)
                self.refresh_points_list()
                self.select_index(len(self.points) - 1)
                self.status_label.config(text=("Click" if action == "click" else "Drag") + " point added", fg="#a6e3a1")
                self.clear_previews()
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value:\n{e}", parent=popup)

        btn_frame = tk.Frame(popup, bg="#1e1e2e")
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="Add", command=apply_add, width=10).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=on_popup_close, width=10).pack(side="left", padx=6)

        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 80
        popup.geometry(f"+{x}+{y}")

    def open_edit_popup(self):
        if self.is_busy() or self.selected_index is None or self.selected_index >= len(self.points):
            return
        p = self.points[self.selected_index]
        action = p.get("action", "click")

        self.clear_previews()
        preview_main = preview_end = None
        if action == "click":
            preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#89b4fa", "C")
        elif action == "drag":
            preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#a6e3a1", "S")
            preview_end = self.show_point_preview(p.get("drag_x", 0), p.get("drag_y", 0), "#f38ba8", "E")
        elif action == "scroll":
            preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#cba6f7", "Sc")

        popup = tk.Toplevel(self.root)
        popup.title("Edit Item")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        # No grab_set when previews exist: allows dragging the on-screen markers
        if action in ("wait", "key"):
            popup.grab_set()

        def on_popup_close():
            self.clear_previews()
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        vcmd = (popup.register(self.validate_number), "%d", "%P")

        tk.Label(popup, text=f"Editing item #{self.selected_index + 1}", font=("Segoe UI", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 6))
        if action in ("click", "drag", "scroll"):
            tk.Label(popup, text="Drag the on-screen marker(s) to reposition",
                     bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=15, pady=(0, 6))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value=p.get("name", ""))
        ttk.Entry(name_frame, textvariable=name_var, width=22).pack(side="left", padx=(6, 0))

        frame = tk.Frame(popup, bg="#1e1e2e")
        frame.pack(padx=15, pady=5)
        entries = {}

        def bind_live_preview(var_x, var_y, preview_win):
            if preview_win is None:
                return

            def on_change(*_):
                self._move_preview(preview_win, var_x, var_y)

            var_x.trace_add("write", on_change)
            var_y.trace_add("write", on_change)
            self.make_preview_draggable(preview_win, var_x, var_y)

        if action == "wait":
            tk.Label(frame, text="Wait Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=p.get("delay", 500))
            ttk.Spinbox(frame, from_=1, to=60000, textvariable=var, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=3, padx=5)
            entries["delay"] = var

        elif action == "key":
            tk.Label(frame, text="Key / Combo:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
            key_var = tk.StringVar(value=p.get("key", "a"))
            ttk.Entry(frame, textvariable=key_var, width=16).grid(row=0, column=1, pady=2, padx=5)
            entries["key"] = key_var
            tk.Label(frame, text="e.g. a  |  ctrl+c  |  shift+3  |  alt+f4",
                     bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=2, sticky="w")
            tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            var_count = tk.IntVar(value=p.get("count", 1))
            ttk.Spinbox(frame, from_=1, to=100, textvariable=var_count, width=10,
                        validate="key", validatecommand=vcmd).grid(row=2, column=1, pady=2, padx=5)
            entries["count"] = var_count
            tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=p.get("delay_after", 100))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        elif action == "scroll":
            tk.Label(frame, text="X:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
            var_x = tk.IntVar(value=p.get("x", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_x, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
            entries["x"] = var_x
            tk.Label(frame, text="Y:", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
            var_y = tk.IntVar(value=p.get("y", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_y, width=10,
                        validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)
            entries["y"] = var_y
            bind_live_preview(var_x, var_y, preview_main)
            tk.Label(frame, text="Direction:", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            dir_var = tk.StringVar(value="UP" if p.get("dy", 0) >= 0 else "DOWN")
            ttk.Combobox(frame, textvariable=dir_var, values=["UP", "DOWN"],
                         state="readonly", width=8).grid(row=2, column=1, pady=2, padx=5)
            entries["direction"] = dir_var
            tk.Label(frame, text="Amount:", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
            amount_var = tk.IntVar(value=abs(p.get("dy", 3)) or 3)
            ttk.Spinbox(frame, from_=1, to=20, textvariable=amount_var, width=10,
                        validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
            entries["amount"] = amount_var
            tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=4, column=0, sticky="w", pady=2)
            var_count = tk.IntVar(value=p.get("count", 1))
            ttk.Spinbox(frame, from_=1, to=100, textvariable=var_count, width=10,
                        validate="key", validatecommand=vcmd).grid(row=4, column=1, pady=2, padx=5)
            entries["count"] = var_count
            tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=p.get("delay_after", 50))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        elif action == "drag":
            labels = [("Start X:", "x"), ("Start Y:", "y"), ("End X:", "drag_x"), ("End Y:", "drag_y"),
                      ("Duration (ms):", "hold"), ("Repeat:", "count"), ("Delay Between Repeats (ms):", "delay_after")]
            for i, (label, key) in enumerate(labels):
                tk.Label(frame, text=label, bg="#1e1e2e", fg="#cdd6f4").grid(row=i, column=0, sticky="w", pady=2)
                var = tk.IntVar(value=p.get(key, 1 if key == "count" else 0))
                max_val = 100 if key == "count" else (99999 if key in ("hold", "delay_after") else 10000)
                from_val = 1 if key == "count" else 0
                ttk.Spinbox(frame, from_=from_val, to=max_val, textvariable=var, width=10,
                            validate="key", validatecommand=vcmd).grid(row=i, column=1, pady=2, padx=5)
                entries[key] = var
            bind_live_preview(entries["x"], entries["y"], preview_main)
            bind_live_preview(entries["drag_x"], entries["drag_y"], preview_end)

        else:
            tk.Label(frame, text="X:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
            var_x = tk.IntVar(value=p.get("x", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_x, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
            entries["x"] = var_x
            tk.Label(frame, text="Y:", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
            var_y = tk.IntVar(value=p.get("y", 0))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_y, width=10,
                        validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)
            entries["y"] = var_y
            bind_live_preview(var_x, var_y, preview_main)
            tk.Label(frame, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            var_hold = tk.IntVar(value=p.get("hold", 50))
            hold_spin = ttk.Spinbox(frame, from_=10, to=2000, textvariable=var_hold, width=10,
                                    validate="key", validatecommand=vcmd)
            hold_spin.grid(row=2, column=1, pady=2, padx=5)
            entries["hold"] = var_hold
            tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
            var_count = tk.IntVar(value=p.get("count", 1))
            ttk.Spinbox(frame, from_=1, to=100, textvariable=var_count, width=10,
                        validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
            entries["count"] = var_count
            tk.Label(frame, text="Type:", bg="#1e1e2e", fg="#cdd6f4").grid(row=4, column=0, sticky="w", pady=2)
            var_type = tk.StringVar(value=p.get("type", "Left"))
            type_combo = ttk.Combobox(frame, textvariable=var_type,
                                      values=["Left", "Right", "Double", "Middle"],
                                      state="readonly", width=8)
            type_combo.grid(row=4, column=1, pady=2, padx=5)
            type_combo.set(p.get("type", "Left"))
            entries["type"] = var_type

            def on_type_change(event=None):
                hold_spin.config(state="disabled" if var_type.get() == "Double" else "normal")

            type_combo.bind("<<ComboboxSelected>>", on_type_change)
            on_type_change()
            tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=p.get("delay_after", 100))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        def apply_changes():
            try:
                p["name"] = name_var.get().strip()
                if action == "wait":
                    p["delay"] = max(1, int(entries["delay"].get()))
                elif action == "key":
                    p["key"] = entries["key"].get().strip().lower()
                    p["count"] = int(entries["count"].get())
                    p["delay_after"] = int(entries["delay_after"].get())
                elif action == "scroll":
                    p["x"] = int(entries["x"].get())
                    p["y"] = int(entries["y"].get())
                    amount = max(1, int(entries["amount"].get()))
                    p["dx"] = 0
                    p["dy"] = amount if entries["direction"].get() == "UP" else -amount
                    p["count"] = int(entries["count"].get())
                    p["delay_after"] = int(entries["delay_after"].get())
                elif action == "drag":
                    for key in ["x", "y", "drag_x", "drag_y", "hold", "count", "delay_after"]:
                        p[key] = int(entries[key].get())
                else:
                    p["x"] = int(entries["x"].get())
                    p["y"] = int(entries["y"].get())
                    p["hold"] = int(entries["hold"].get())
                    p["count"] = int(entries["count"].get())
                    p["type"] = entries["type"].get()
                    p["delay_after"] = int(entries["delay_after"].get())
                self.refresh_points_list()
                self.select_index(self.selected_index)
                self.status_label.config(text="Item updated", fg="#a6e3a1")
                self.clear_previews()
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value:\n{e}", parent=popup)

        btn_frame = tk.Frame(popup, bg="#1e1e2e")
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="Apply", command=apply_changes, width=10).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=on_popup_close, width=10).pack(side="left", padx=6)

        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 80
        popup.geometry(f"+{x}+{y}")

    def add_wait(self):
        if self.is_busy():
            return
        popup = tk.Toplevel(self.root)
        popup.title("Add Wait")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        vcmd = (popup.register(self.validate_number), "%d", "%P")
        tk.Label(popup, text="Wait Duration", font=("Segoe UI", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 8))

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value="")
        ttk.Entry(name_frame, textvariable=name_var, width=18).pack(side="left", padx=(6, 0))

        row = tk.Frame(popup, bg="#1e1e2e")
        row.pack(padx=20, pady=4)
        tk.Label(row, text="Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        delay_var = tk.IntVar(value=500)
        ttk.Spinbox(row, from_=1, to=60000, textvariable=delay_var, width=10,
                    validate="key", validatecommand=vcmd).pack(side="left", padx=(8, 0))

        def apply():
            try:
                delay = max(1, int(delay_var.get()))
            except Exception:
                delay = 500
            self.points.append({"action": "wait", "delay": delay, "name": name_var.get().strip()})
            self.refresh_points_list()
            self.select_index(len(self.points) - 1)
            self.status_label.config(text=f"Wait {delay}ms added", fg="#a6e3a1")
            popup.destroy()

        btn_row = tk.Frame(popup, bg="#1e1e2e")
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text="Add", command=apply, width=8).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel", command=popup.destroy, width=8).pack(side="left", padx=4)
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 100
        popup.geometry(f"+{x}+{y}")
        popup.bind("<Return>", lambda e: apply())

    def start_add_scroll(self):
        """Capture scroll position first, then open the settings popup (same flow as Click/Drag)."""
        if self.is_busy():
            return
        if self.click_listener and self.click_listener.is_alive():
            try:
                self.click_listener.stop()
            except Exception:
                pass
            self.click_listener = None
        self.minimize_for_capture()
        self.status_label.config(text="Click to set scroll position...", fg="#f9e2af")

        def on_click(x, y, button, pressed):
            if button != Button.left or not pressed:
                return True

            def finish():
                if self.click_listener:
                    try:
                        if self.click_listener.is_alive():
                            self.click_listener.stop()
                    except Exception:
                        pass
                    self.click_listener = None
                self.restore_after_capture()
                self.status_label.config(text="Set scroll properties...", fg="#f9e2af")
                self.root.after(120, lambda: self.add_scroll_action(preset={"x": x, "y": y}))

            self.root.after(0, finish)
            return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def add_scroll_action(self, preset=None):
        if self.is_busy():
            return
        if preset is None:
            preset = {}
        self.clear_previews()
        preview_main = self.show_point_preview(preset.get("x", 0), preset.get("y", 0), "#cba6f7", "Sc")

        popup = tk.Toplevel(self.root)
        popup.title("Add Scroll")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        # No grab_set so the on-screen marker stays draggable
        vcmd = (popup.register(self.validate_number), "%d", "%P")

        tk.Label(popup, text="Add Mouse Scroll", font=("Segoe UI", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 4))
        tk.Label(popup, text="Drag the on-screen marker to reposition",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=15, pady=(6, 0))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value="")
        ttk.Entry(name_frame, textvariable=name_var, width=18).pack(side="left", padx=(6, 0))

        frame = tk.Frame(popup, bg="#1e1e2e")
        frame.pack(padx=15, pady=8)
        tk.Label(frame, text="X:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
        var_x = tk.IntVar(value=preset.get("x", 0))
        ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_x, width=10,
                    validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
        tk.Label(frame, text="Y:", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
        var_y = tk.IntVar(value=preset.get("y", 0))
        ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_y, width=10,
                    validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)

        def on_xy_change(*_):
            self._move_preview(preview_main, var_x, var_y)
        var_x.trace_add("write", on_xy_change)
        var_y.trace_add("write", on_xy_change)
        self.make_preview_draggable(preview_main, var_x, var_y)

        tk.Label(frame, text="Direction:", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
        dir_var = tk.StringVar(value=preset.get("direction", "UP"))
        ttk.Combobox(frame, textvariable=dir_var, values=["UP", "DOWN"],
                     state="readonly", width=8).grid(row=2, column=1, pady=2, padx=5)
        tk.Label(frame, text="Amount:", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
        amount_var = tk.IntVar(value=preset.get("amount", 3))
        ttk.Spinbox(frame, from_=1, to=20, textvariable=amount_var, width=10,
                    validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
        tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=4, column=0, sticky="w", pady=2)
        count_var = tk.IntVar(value=preset.get("count", 1))
        ttk.Spinbox(frame, from_=1, to=100, textvariable=count_var, width=10,
                    validate="key", validatecommand=vcmd).grid(row=4, column=1, pady=2, padx=5)
        tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
        delay_var = tk.IntVar(value=preset.get("delay_after", 50))
        ttk.Spinbox(frame, from_=0, to=10000, textvariable=delay_var, width=10,
                    validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)

        def on_popup_close():
            self.clear_previews()
            popup.destroy()
            self.status_label.config(text="Add cancelled", fg="#f9e2af")

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)

        def apply():
            try:
                x, y = int(var_x.get()), int(var_y.get())
                amount = max(1, int(amount_var.get()))
                count = max(1, int(count_var.get()))
                delay_after = max(0, int(delay_var.get()))
            except Exception:
                messagebox.showerror("Error", "Invalid values", parent=popup)
                return
            direction = dir_var.get()
            self.points.append({
                "action": "scroll", "x": x, "y": y, "dx": 0,
                "dy": amount if direction == "UP" else -amount,
                "count": count, "delay_after": delay_after,
                "name": name_var.get().strip()
            })
            self.refresh_points_list()
            self.select_index(len(self.points) - 1)
            self.status_label.config(text=f"Scroll {direction} added", fg="#a6e3a1")
            self.clear_previews()
            popup.destroy()

        btn_row = tk.Frame(popup, bg="#1e1e2e")
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="Add", command=apply, width=8).pack(side="left", padx=3)
        ttk.Button(btn_row, text="Cancel", command=on_popup_close, width=8).pack(side="left", padx=3)
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 80
        popup.geometry(f"+{x}+{y}")

    def add_key_action(self):
        if self.is_busy():
            return
        popup = tk.Toplevel(self.root)
        popup.title("Add Keyboard Action")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        tk.Label(popup, text="Key or combination", font=("Segoe UI", 10, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 4))
        tk.Label(popup, text="Type manually or Capture (Ctrl/Alt/Shift/Cmd + key)",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value="")
        ttk.Entry(name_frame, textvariable=name_var, width=18).pack(side="left", padx=(6, 0))

        key_var = tk.StringVar(value="")
        entry = ttk.Entry(popup, textvariable=key_var, width=22, font=("Segoe UI", 11))
        entry.pack(pady=8)
        entry.focus_set()
        tk.Label(popup, text="Examples:  AaBb  |  ctrl+c  |  shift+3  |  alt+F4  |  cmd+v",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        def capture_from_listener():
            self.status_label.config(text="Hold modifiers, then press the key...", fg="#f9e2af")
            held_mods = set()

            def on_press(key):
                try:
                    name = key_to_str(key, held_mods)
                    if name in ("ctrl", "alt", "shift", "cmd"):
                        held_mods.add(name)
                        return True
                    order = ["ctrl", "alt", "shift", "cmd"]
                    mods = [m for m in order if m in held_mods]
                    combo = "+".join(mods + [name]) if mods else name
                    self.root.after(0, lambda c=combo: key_var.set(c))
                    self.root.after(0, lambda c=combo: self.status_label.config(
                        text=f"Captured: {c}", fg="#a6e3a1"))
                    return False
                except Exception:
                    pass
                return True

            def on_release(key):
                try:
                    name = key_to_str(key)
                    if name in ("ctrl", "alt", "shift", "cmd"):
                        held_mods.discard(name)
                except Exception:
                    pass
                return True

            KeyboardListener(on_press=on_press, on_release=on_release).start()

        def apply():
            k = key_var.get().strip().lower()
            if not k:
                messagebox.showwarning("Warning", "Enter or capture a key / combo.", parent=popup)
                return
            self.points.append({
                "action": "key", "key": k,
                "count": 1,
                "delay_after": 100,
                "name": name_var.get().strip()
            })
            self.refresh_points_list()
            self.select_index(len(self.points) - 1)
            self.status_label.config(text=f"Key '{k}' added", fg="#a6e3a1")
            popup.destroy()

        btn_row = tk.Frame(popup, bg="#1e1e2e")
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="Capture Key", command=capture_from_listener, width=12).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Add", command=apply, width=8).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel", command=popup.destroy, width=8).pack(side="left", padx=4)
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 100
        popup.geometry(f"+{x}+{y}")

    def minimize_for_capture(self):
        self.root.iconify()

    def restore_after_capture(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.after(150, lambda: self.root.attributes("-topmost", self.always_on_top.get()))

    def start_add_point(self, mode):
        if self.is_busy():
            return
        if self.click_listener and self.click_listener.is_alive():
            try:
                self.click_listener.stop()
            except Exception:
                pass
            self.click_listener = None
        self.adding_mode = mode
        self.temp_drag_start = None
        self.minimize_for_capture()
        self.status_label.config(
            text="Click to add a new CLICK point..." if mode == "click"
            else "Press & hold, then release to set DRAG...",
            fg="#f9e2af")

        def on_click(x, y, button, pressed):
            if button != Button.left:
                return
            if self.adding_mode == "click" and pressed:
                self.root.after(0, self.finish_add_point_and_edit, "click",
                                {"x": x, "y": y, "hold": 50, "count": 1,
                                 "delay_after": 100, "type": "Left", "name": ""})
                return False
            if self.adding_mode == "drag" and pressed:
                self.temp_drag_start = (x, y)
                self.adding_mode = "drag_release"
                return True
            if self.adding_mode == "drag_release" and not pressed and self.temp_drag_start is not None:
                self.root.after(0, self.finish_add_point_and_edit, "drag", {
                    "x": self.temp_drag_start[0], "y": self.temp_drag_start[1],
                    "drag_x": x, "drag_y": y,
                    "hold": 300, "count": 1, "delay_after": 100, "type": "Left", "name": ""
                })
                return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def finish_add_point_and_edit(self, action, data):
        """After capturing coordinates, restore UI and open the Add/Edit-style popup."""
        self.adding_mode = None
        self.temp_drag_start = None
        if self.click_listener:
            try:
                if self.click_listener.is_alive():
                    self.click_listener.stop()
            except Exception:
                pass
            self.click_listener = None
        self.restore_after_capture()
        self.status_label.config(text="Set properties for the new point...", fg="#f9e2af")
        self.root.after(120, lambda: self.open_add_popup(action, data))

    def toggle_recording(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Stop the running sequence first.")
            return
        if self.is_recording:
            self.stop_recording(from_ui=True)
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_running or self.is_recording:
            return
        self.is_recording = True
        self.record_events = []
        self.record_start_time = time.time()
        self.record_btn.config(text="Stop Rec")
        self.set_record_indicator(True)
        self.status_label.config(text=f"Recording... Press {self.record_stop_hotkey.upper()} to stop", fg="#f38ba8")
        self.minimize_for_capture()

        for lst in (self.record_mouse_listener, self.record_keyboard_listener):
            if lst and getattr(lst, "is_alive", lambda: False)():
                try:
                    lst.stop()
                except Exception:
                    pass

        self._rec_drag_start = None
        self._rec_last_time = self.record_start_time
        self._rec_held_mods = set()

        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
            now = time.time()
            delay_ms = int((now - self._rec_last_time) * 1000)
            self._rec_last_time = now
            btn_name = {Button.right: "Right", Button.middle: "Middle"}.get(button, "Left")
            if pressed:
                self._rec_drag_start = (x, y, btn_name, delay_ms)
            elif self._rec_drag_start:
                sx, sy, bname, dly = self._rec_drag_start
                if dly > 30:
                    self.record_events.append({"action": "wait", "delay": dly, "name": ""})
                if abs(x - sx) > 5 or abs(y - sy) > 5:
                    self.record_events.append({
                        "action": "drag", "x": sx, "y": sy, "drag_x": x, "drag_y": y,
                        "hold": 750,
                        "count": 1, "delay_after": 50, "type": "Left", "name": ""
                    })
                else:
                    self.record_events.append({
                        "action": "click", "x": sx, "y": sy, "hold": 50,
                        "count": 1, "delay_after": 50, "type": bname, "name": ""
                    })
                self._rec_drag_start = None
            return True

        def on_scroll(x, y, dx, dy):
            if not self.is_recording:
                return False
            now = time.time()
            delay_ms = int((now - self._rec_last_time) * 1000)
            self._rec_last_time = now
            if delay_ms > 30:
                self.record_events.append({"action": "wait", "delay": delay_ms, "name": ""})
            if dy == 0:
                return True
            self.record_events.append({
                "action": "scroll", "x": x, "y": y, "dx": 0, "dy": int(dy),
                "count": 1, "delay_after": 30, "name": ""
            })
            return True

        def on_press(key):
            if not self.is_recording:
                return False
            kstr = key_to_str(key, self._rec_held_mods)
            if kstr == self.record_stop_hotkey:
                return True
            if kstr in ("ctrl", "alt", "shift", "cmd"):
                self._rec_held_mods.add(kstr)
                return True
            now = time.time()
            delay_ms = int((now - self._rec_last_time) * 1000)
            self._rec_last_time = now
            if delay_ms > 30:
                self.record_events.append({"action": "wait", "delay": delay_ms, "name": ""})
            order = ["ctrl", "alt", "shift", "cmd"]
            mods = [m for m in order if m in self._rec_held_mods]
            combo = "+".join(mods + [kstr]) if mods else kstr
            self.record_events.append({
                "action": "key", "key": combo, "count": 1, "delay_after": 50, "name": ""
            })
            return True

        def on_release(key):
            if not self.is_recording:
                return False
            try:
                name = key_to_str(key)
                if name in ("ctrl", "alt", "shift", "cmd"):
                    self._rec_held_mods.discard(name)
            except Exception:
                pass
            return True

        self.record_mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
        self.record_mouse_listener.start()
        self.record_keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)
        self.record_keyboard_listener.start()

    def stop_recording(self, from_ui=False):
        self.is_recording = False
        for attr in ("record_mouse_listener", "record_keyboard_listener"):
            lst = getattr(self, attr)
            if lst:
                try:
                    if lst.is_alive():
                        lst.stop()
                except Exception:
                    pass
                setattr(self, attr, None)

        if from_ui and self.record_events:
            if self.record_events[-1].get("action") == "click":
                self.record_events.pop()
                if self.record_events and self.record_events[-1].get("action") == "wait":
                    self.record_events.pop()

        count_before = len(self.points)
        self.points.extend(self.record_events)
        added = len(self.points) - count_before
        self.record_events = []
        self.refresh_points_list()
        if self.points:
            self.select_index(len(self.points) - 1)
        self.restore_after_capture()
        self.record_btn.config(text="Record")
        self.set_record_indicator(False)
        self.status_label.config(text=f"Recording stopped — {added} actions added", fg="#a6e3a1")

    def move_up(self):
        if self.selected_index is None or self.selected_index == 0 or self.is_busy():
            return
        i = self.selected_index
        self.points[i], self.points[i - 1] = self.points[i - 1], self.points[i]
        self.refresh_points_list()
        self.select_index(i - 1)

    def move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.points) - 1 or self.is_busy():
            return
        i = self.selected_index
        self.points[i], self.points[i + 1] = self.points[i + 1], self.points[i]
        self.refresh_points_list()
        self.select_index(i + 1)

    def remove_point(self):
        if self.is_busy() or self.selected_index is None:
            return
        idx = self.selected_index
        del self.points[idx]
        self.refresh_points_list()
        if self.points:
            self.select_index(min(idx, len(self.points) - 1))
        else:
            self.selected_index = None
            self.edit_btn.config(state="disabled")
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_busy():
            return
        self.points.clear()
        self.selected_index = None
        self.edit_btn.config(state="disabled")
        self.refresh_points_list()
        self.status_label.config(text="All points cleared", fg="#f9e2af")

    def toggle_infinite(self):
        self.rep_spin.config(state="disabled" if self.infinite.get() else "normal")

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    def change_hotkey(self, which):
        self.force_english_keyboard()
        self.waiting_for_hotkey = which
        labels = {
            "start": "START", "pause": "PAUSE/RESUME", "stop": "STOP",
            "record_start": "START RECORD", "record_stop": "STOP RECORD"
        }
        self.status_label.config(text=f"Press a key for {labels.get(which, which.upper())}...", fg="#f9e2af")

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                kstr = key_to_str(key)
                if self.waiting_for_hotkey:
                    if key == Key.esc:
                        self.waiting_for_hotkey = None
                        self.status_label.config(text="Cancelled", fg="#f9e2af")
                        return
                    if not kstr or kstr in ("ctrl", "alt", "shift", "cmd"):
                        return
                    # Disallow media / system special keys (volume, play/pause, brightness, etc.)
                    # Function keys (F1–F12) are still allowed.
                    kstr_lower = kstr.lower().replace("key.", "").replace(" ", "_")
                    is_media = (
                        kstr_lower.startswith(("media_", "volume_", "brightness_", "launch_", "browser_"))
                        or any(s in kstr_lower for s in (
                            "volume_up", "volume_down", "volume_mute",
                            "play_pause", "next_track", "prev_track", "stop_media",
                            "media_play", "media_pause", "media_stop",
                        ))
                    )
                    if is_media:
                        self.status_label.config(text="Media/system keys not allowed!", fg="#f38ba8")
                        self.waiting_for_hotkey = None
                        return
                    all_hk = {
                        "start": self.start_hotkey, "pause": self.pause_hotkey,
                        "stop": self.stop_hotkey,
                        "record_start": self.record_start_hotkey, "record_stop": self.record_stop_hotkey
                    }
                    for name, val in all_hk.items():
                        if name != self.waiting_for_hotkey and val == kstr:
                            self.status_label.config(text="Same key not allowed!", fg="#f38ba8")
                            self.waiting_for_hotkey = None
                            return
                    if self.waiting_for_hotkey == "start":
                        self.start_hotkey = kstr
                        self.start_hk_label.config(text=f"▶ Start: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "pause":
                        self.pause_hotkey = kstr
                        self.pause_hk_label.config(text=f"⏸ Pause: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "stop":
                        self.stop_hotkey = kstr
                        self.stop_hk_label.config(text=f"⏹ Stop: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "record_start":
                        self.record_start_hotkey = kstr
                        self.record_start_hk_label.config(text=f"⏺ Start Rec: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "record_stop":
                        self.record_stop_hotkey = kstr
                        self.record_stop_hk_label.config(text=f"⏹ Stop Rec: {kstr.upper()}")
                    self.status_label.config(text=f"Hotkey → {kstr.upper()}", fg="#a6e3a1")
                    self.waiting_for_hotkey = None
                    return

                if self.is_focus_on_input():
                    return
                if (self.rs_hotkey_enabled.get() and kstr == self.record_start_hotkey
                        and not self.is_recording and not self.is_running):
                    self.root.after(0, self.start_recording)
                    return
                if (self.re_hotkey_enabled.get() and self.is_recording
                        and kstr == self.record_stop_hotkey):
                    self.root.after(0, lambda: self.stop_recording(from_ui=False))
                    return
                if (self.g_hotkey_enabled.get() and kstr == self.start_hotkey
                        and not self.is_running and not self.is_recording):
                    self.root.after(0, self.start_clicking)
                    return
                if (self.p_hotkey_enabled.get() and kstr == self.pause_hotkey
                        and self.is_running):
                    self.root.after(0, self.toggle_pause)
                    return
                if (self.s_hotkey_enabled.get() and kstr == self.stop_hotkey
                        and self.is_running):
                    self.root.after(0, self.stop_clicking)
            except Exception:
                pass

        self.keyboard_listener = KeyboardListener(on_press=on_press)
        self.keyboard_listener.start()

    def get_safe_int(self, var, default, min_val=0, max_val=999999):
        try:
            return max(min_val, min(int(var.get()), max_val))
        except Exception:
            return default

    def start_clicking(self):
        if not self.points:
            messagebox.showwarning("Warning", "Add at least one point!")
            return
        if self.is_running or self.is_recording:
            return
        self.is_running = True
        self.is_paused = False
        self.stop_flag = False
        self.current_cycle = 0
        self.current_step_index = 0
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal", text="Pause")
        self.stop_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.record_btn.config(state="disabled")
        self.set_speed_controls_state(False)
        self.status_label.config(text="Running...", fg="#89b4fa")
        self.progress_label.config(text="")
        random_ms = self.get_safe_int(self.random_var, 0, 0, 500)
        pos_rand = self.get_safe_int(self.pos_random_var, 0, 0, 50)
        cycles = self.get_safe_int(self.rep_var, 1, 1, 99999)
        threading.Thread(target=self.click_loop, args=(random_ms, pos_rand, cycles), daemon=True).start()

    def toggle_pause(self):
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="Resume")
            self.status_label.config(text="Paused — edit list freely, then Resume", fg="#f9e2af")
            if self.selected_index is not None and self.selected_index < len(self.points):
                self.edit_btn.config(state="normal")
            self.set_speed_controls_state(True)
        else:
            self.pause_btn.config(text="Pause")
            self.status_label.config(text="Running...", fg="#89b4fa")
            self.edit_btn.config(state="disabled")
            self.set_speed_controls_state(False)

    def apply_pos_random(self, x, y, pos_rand):
        if pos_rand <= 0:
            return x, y
        return x + random.randint(-pos_rand, pos_rand), y + random.randint(-pos_rand, pos_rand)

    def wait_if_paused(self):
        """Block while paused; return True if should abort (stop_flag)."""
        while self.is_paused and not self.stop_flag:
            time.sleep(0.05)
        return self.stop_flag

    def get_speed_factor(self):
        try:
            v = float(self.speed_var.get())
            return max(0.1, min(20.0, v))
        except Exception:
            return 1.0

    def interruptible_sleep(self, duration_ms):
        """Sleep in small chunks so stop/pause can react immediately. Respects global speed."""
        if duration_ms <= 0:
            return
        factor = self.get_speed_factor()
        scaled = duration_ms / factor
        end = time.time() + scaled / 1000.0
        while time.time() < end:
            if self.stop_flag:
                return
            if self.wait_if_paused():
                return
            remaining = end - time.time()
            time.sleep(min(0.05, max(0, remaining)))

    def perform_click(self, p, pos_rand):
        x, y = self.apply_pos_random(p["x"], p["y"], pos_rand)
        hold, typ = p.get("hold", 50), p.get("type", "Left")
        btn = {"Left": Button.left, "Right": Button.right, "Middle": Button.middle}.get(typ, Button.left)
        self.mouse.position = (x, y)
        if typ == "Double":
            self.mouse.click(btn, 2)
        else:
            self.mouse.press(btn)
            self.interruptible_sleep(hold)
            self.mouse.release(btn)

    def perform_drag(self, p, pos_rand):
        sx, sy = self.apply_pos_random(p["x"], p["y"], pos_rand)
        ex, ey = self.apply_pos_random(p["drag_x"], p["drag_y"], pos_rand)
        factor = self.get_speed_factor()
        duration = (p.get("hold", 300) / factor) / 1000.0
        self.mouse.position = (sx, sy)
        self.mouse.press(Button.left)
        steps = max(8, int(duration * 50))
        for i in range(1, steps + 1):
            if self.stop_flag or self.wait_if_paused():
                break
            t = i / steps
            self.mouse.position = (int(sx + (ex - sx) * t), int(sy + (ey - sy) * t))
            time.sleep(duration / steps)
        self.mouse.release(Button.left)

    def perform_key(self, p):
        modifiers, main = parse_key_combo(p.get("key", "a"))
        main_obj = str_to_key(main)
        try:
            for mod in modifiers:
                self.keyboard.press(mod)
            try:
                self.keyboard.press(main_obj)
                self.keyboard.release(main_obj)
            except Exception:
                self.keyboard.press(main)
                self.keyboard.release(main)
            for mod in reversed(modifiers):
                self.keyboard.release(mod)
        except Exception:
            try:
                self.keyboard.press(main_obj)
                self.keyboard.release(main_obj)
            except Exception:
                pass

    def perform_scroll(self, p, pos_rand):
        x, y = self.apply_pos_random(p.get("x", 0), p.get("y", 0), pos_rand)
        self.mouse.position = (x, y)
        self.mouse.scroll(p.get("dx", 0), p.get("dy", 0))

    def click_loop(self, random_ms, pos_rand, max_cycles):
        cycle = 0
        if self.infinite.get():
            max_cycles = float("inf")
        while not self.stop_flag and cycle < max_cycles:
            self.current_cycle = cycle
            idx = 0
            while idx < len(self.points):
                if self.stop_flag:
                    break
                if self.wait_if_paused():
                    break

                # Re-validate index after possible list edits during pause
                if idx >= len(self.points):
                    break

                p = self.points[idx]
                self.current_step_index = idx
                total_points = len(self.points)

                self.root.after(0, self.highlight_current, idx)
                if self.infinite.get():
                    prog = f"Cycle {cycle + 1} (∞)  |  Step {idx + 1}/{total_points}"
                else:
                    pct = int(((cycle * total_points + idx) / (max_cycles * total_points)) * 100) if max_cycles * total_points else 0
                    prog = f"Cycle {cycle + 1}/{max_cycles}  |  Step {idx + 1}/{total_points}  |  {pct}%"
                self.root.after(0, lambda t=prog: self.progress_label.config(text=t))

                action = p.get("action")
                if action == "wait":
                    delay = p.get("delay", 500)
                    if random_ms > 0:
                        delay += random.randint(-random_ms, random_ms)
                    self.interruptible_sleep(max(0, delay))
                    idx += 1
                    continue

                count = p.get("count", 1)
                delay_between = p.get("delay_after", 0)
                runners = {
                    "drag": self.perform_drag,
                    "key": lambda pt, pr: self.perform_key(pt),
                    "scroll": self.perform_scroll,
                }
                runner = runners.get(action, self.perform_click)
                for i in range(count):
                    if self.stop_flag:
                        break
                    if self.wait_if_paused():
                        break
                    # Re-fetch in case the step was edited during pause
                    if idx >= len(self.points):
                        break
                    p = self.points[idx]
                    action = p.get("action")
                    if action == "key":
                        self.perform_key(p)
                    elif action == "wait":
                        break  # type changed to wait mid-run; skip to next
                    else:
                        runner = runners.get(action, self.perform_click)
                        runner(p, pos_rand)
                    if i < count - 1 and delay_between > 0:
                        d = delay_between + (random.randint(-random_ms, random_ms) if random_ms > 0 else 0)
                        self.interruptible_sleep(max(0, d))
                idx += 1
            cycle += 1
        self.is_running = False
        self.is_paused = False
        self.root.after(0, self.on_clicking_finished)

    def on_clicking_finished(self):
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Pause")
        self.stop_btn.config(state="disabled")
        self.record_btn.config(state="normal")
        self.set_speed_controls_state(True)
        self.clear_highlight()
        if self.selected_index is not None and self.selected_index < len(self.points):
            self.edit_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")
        self.progress_label.config(text="")

    def stop_clicking(self):
        self.stop_flag = True
        self.is_paused = False  # unblock any wait_if_paused loops
        self.status_label.config(text="Stopping...", fg="#f9e2af")

    def save_profile(self):
        data = {
            "points": self.points,
            "random": self.random_var.get(),
            "pos_random": self.pos_random_var.get(),
            "cycles": self.rep_var.get(),
            "infinite": self.infinite.get(),
            "speed": self.speed_var.get(),
            "start_hotkey": self.start_hotkey,
            "pause_hotkey": self.pause_hotkey,
            "stop_hotkey": self.stop_hotkey,
            "record_start_hotkey": self.record_start_hotkey,
            "record_stop_hotkey": self.record_stop_hotkey,
            "start_enabled": self.g_hotkey_enabled.get(),
            "pause_enabled": self.p_hotkey_enabled.get(),
            "stop_enabled": self.s_hotkey_enabled.get(),
            "record_start_enabled": self.rs_hotkey_enabled.get(),
            "record_stop_enabled": self.re_hotkey_enabled.get(),
            "always_on_top": self.always_on_top.get(),
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Profile", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                self.status_label.config(text="Profile saved", fg="#a6e3a1")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def load_profile(self):
        if self.is_running or self.is_recording:
            messagebox.showwarning("Warning", "Stop first.")
            return

        path = filedialog.askopenfilename(filetypes=[("JSON Profile", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.points = data.get("points", [])
            for p in self.points:
                p.setdefault("name", "")
            self.refresh_points_list()
            self.random_var.set(data.get("random", 0))
            self.pos_random_var.set(data.get("pos_random", 0))
            self.rep_var.set(data.get("cycles", 1))
            self.infinite.set(data.get("infinite", False))
            self.toggle_infinite()
            try:
                self.speed_var.set(float(data.get("speed", 1.0)))
                self._on_speed_change()
            except Exception:
                self.speed_var.set(1.0)
                self._on_speed_change()
            self.start_hotkey = data.get("start_hotkey", "f1")
            self.pause_hotkey = data.get("pause_hotkey", "f2")
            self.stop_hotkey = data.get("stop_hotkey", "f3")
            self.record_start_hotkey = data.get("record_start_hotkey", "f4")
            self.record_stop_hotkey = data.get("record_stop_hotkey", "f5")
            self.start_hk_label.config(text=f"▶ Start: {self.start_hotkey.upper()}")
            self.pause_hk_label.config(text=f"⏸ Pause: {self.pause_hotkey.upper()}")
            self.stop_hk_label.config(text=f"⏹ Stop: {self.stop_hotkey.upper()}")
            self.record_start_hk_label.config(text=f"⏺ Start Rec: {self.record_start_hotkey.upper()}")
            self.record_stop_hk_label.config(text=f"⏹ Stop Rec: {self.record_stop_hotkey.upper()}")
            self.g_hotkey_enabled.set(data.get("start_enabled", True))
            self.p_hotkey_enabled.set(data.get("pause_enabled", True))
            self.s_hotkey_enabled.set(data.get("stop_enabled", True))
            self.rs_hotkey_enabled.set(data.get("record_start_enabled", True))
            self.re_hotkey_enabled.set(data.get("record_stop_enabled", True))
            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_topmost()
            self.selected_index = None
            self.edit_btn.config(state="disabled")
            self.status_label.config(text="Profile loaded", fg="#a6e3a1")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exit_app(self):
        self.stop_flag = True
        self.is_paused = False
        self.is_running = False
        self.is_recording = False
        self.clear_previews()
        for listener in [self.click_listener, self.keyboard_listener,
                         self.record_mouse_listener, self.record_keyboard_listener]:
            if listener:
                try:
                    if hasattr(listener, "is_alive") and listener.is_alive():
                        listener.stop()
                except Exception:
                    pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
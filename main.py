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


def key_to_str(key):
    if isinstance(key, KeyCode):
        if key.char:
            return key.char.lower()
        if key.vk is not None:
            return f"vk_{key.vk}"
    if isinstance(key, Key):
        name = str(key).replace("Key.", "")
        return name.lower()
    return str(key).lower()


def str_to_key(s):
    s = s.lower().strip()
    if s in SPECIAL_KEYS:
        return SPECIAL_KEYS[s]
    if len(s) == 1:
        return s
    return s


class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)
        self.version = "v4.2"

        self.points = []
        self.selected_index = None
        self.is_running = False
        self.stop_flag = False
        self.is_recording = False
        self.clipboard_point = None  # for copy/cut/paste

        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)

        self.start_hotkey = "f1"
        self.stop_hotkey = "f2"
        self.record_stop_hotkey = "f3"

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
        self.root.geometry(f"520x{self.root.winfo_reqheight()}")

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

    def validate_number(self, action, value_if_allowed):
        if action == "1":
            return value_if_allowed.isdigit() or value_if_allowed == ""
        return True

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground="#313244",
                        background="#313244",
                        foreground="#cdd6f4",
                        arrowcolor="#cdd6f4",
                        bordercolor="#45475a",
                        darkcolor="#313244",
                        lightcolor="#313244",
                        selectbackground="#313244",
                        selectforeground="#cdd6f4")
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

        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 15, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(6, 3))

        settings_frame = ttk.LabelFrame(self.root, text=" Defaults for New Points ", padding=5)
        settings_frame.pack(fill="x", padx=10, pady=2)

        row1 = tk.Frame(settings_frame, bg="#1e1e2e")
        row1.pack(fill="x", pady=1)
        tk.Label(row1, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4", width=14, anchor="w").pack(side="left")
        self.pt_hold_var = tk.IntVar(value=50)
        self.pt_hold_spin = ttk.Spinbox(row1, from_=10, to=2000, textvariable=self.pt_hold_var, width=7,
                                        validate="key", validatecommand=vcmd)
        self.pt_hold_spin.pack(side="left")
        tk.Label(row1, text=" Repeat:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(8, 0))
        self.pt_count_var = tk.IntVar(value=1)
        ttk.Spinbox(row1, from_=1, to=100, textvariable=self.pt_count_var, width=5,
                    validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(row1, text=" Type:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(8, 0))
        self.pt_type_var = tk.StringVar(value="Left")
        self.pt_type_combo = ttk.Combobox(row1, textvariable=self.pt_type_var,
                                          values=["Left", "Right", "Double", "Middle"],
                                          state="readonly", width=8)
        self.pt_type_combo.pack(side="left")
        self.pt_type_combo.set("Left")
        self.pt_type_combo.bind("<<ComboboxSelected>>", self.on_default_type_change)

        row2 = tk.Frame(settings_frame, bg="#1e1e2e")
        row2.pack(fill="x", pady=1)
        tk.Label(row2, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4", width=22, anchor="w").pack(side="left")
        self.pt_delay_var = tk.IntVar(value=100)
        ttk.Spinbox(row2, from_=0, to=10000, textvariable=self.pt_delay_var, width=7,
                    validate="key", validatecommand=vcmd).pack(side="left")

        points_frame = ttk.LabelFrame(self.root, text=" Points Sequence (Drag items to reorder) ", padding=5)
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
        ttk.Button(btn_row, text="Add Wait", command=self.add_wait).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="Add Key", command=self.add_key_action).pack(side="left", expand=True, fill="x", padx=(2, 0))

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

        global_frame = ttk.LabelFrame(self.root, text=" Global Settings ", padding=5)
        global_frame.pack(fill="x", padx=10, pady=2)

        rowg1 = tk.Frame(global_frame, bg="#1e1e2e")
        rowg1.pack(fill="x", pady=1)
        tk.Label(rowg1, text="Random Time ±ms:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.random_var = tk.IntVar(value=0)
        ttk.Spinbox(rowg1, from_=0, to=500, textvariable=self.random_var, width=5,
                    validate="key", validatecommand=vcmd).pack(side="left", padx=(3, 12))
        tk.Label(rowg1, text="Random Position ±px:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.pos_random_var = tk.IntVar(value=0)
        ttk.Spinbox(rowg1, from_=0, to=50, textvariable=self.pos_random_var, width=4,
                    validate="key", validatecommand=vcmd).pack(side="left", padx=(3, 0))

        rowg2 = tk.Frame(global_frame, bg="#1e1e2e")
        rowg2.pack(fill="x", pady=2)
        tk.Label(rowg2, text="Cycles:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.rep_var = tk.IntVar(value=1)
        self.rep_spin = ttk.Spinbox(rowg2, from_=1, to=99999, textvariable=self.rep_var, width=6,
                                    validate="key", validatecommand=vcmd)
        self.rep_spin.pack(side="left", padx=(3, 12))
        ttk.Checkbutton(rowg2, text="Infinite", variable=self.infinite,
                        command=self.toggle_infinite).pack(side="left")

        rowg3 = tk.Frame(global_frame, bg="#1e1e2e")
        rowg3.pack(fill="x", pady=2)
        ttk.Checkbutton(rowg3, text="Always on Top", variable=self.always_on_top,
                        command=self.toggle_topmost).pack(side="left")

        hotkey_frame = ttk.LabelFrame(self.root, text=" Hotkeys ", padding=5)
        hotkey_frame.pack(fill="x", padx=10, pady=2)

        hk1 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk1.pack(fill="x", pady=1)
        self.start_hk_label = tk.Label(hk1, text=f"Start Hotkey: {self.start_hotkey.upper()}",
                                       bg="#1e1e2e", fg="#cdd6f4", width=22, anchor="w")
        self.start_hk_label.pack(side="left")
        ttk.Button(hk1, text="Change", width=7, command=lambda: self.change_hotkey("start")).pack(side="left", padx=4)
        ttk.Checkbutton(hk1, text="Enable", variable=self.g_hotkey_enabled).pack(side="left")

        hk2 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk2.pack(fill="x", pady=1)
        self.stop_hk_label = tk.Label(hk2, text=f"Stop Hotkey: {self.stop_hotkey.upper()}",
                                      bg="#1e1e2e", fg="#cdd6f4", width=22, anchor="w")
        self.stop_hk_label.pack(side="left")
        ttk.Button(hk2, text="Change", width=7, command=lambda: self.change_hotkey("stop")).pack(side="left", padx=4)
        ttk.Checkbutton(hk2, text="Enable", variable=self.s_hotkey_enabled).pack(side="left")

        hk3 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk3.pack(fill="x", pady=1)
        self.record_stop_hk_label = tk.Label(hk3, text=f"Stop Record: {self.record_stop_hotkey.upper()}",
                                             bg="#1e1e2e", fg="#cdd6f4", width=22, anchor="w")
        self.record_stop_hk_label.pack(side="left")
        ttk.Button(hk3, text="Change", width=7, command=lambda: self.change_hotkey("record_stop")).pack(side="left", padx=4)

        profile_frame = tk.Frame(self.root, bg="#1e1e2e")
        profile_frame.pack(fill="x", padx=10, pady=3)
        ttk.Button(profile_frame, text="Save Profile", command=self.save_profile).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(profile_frame, text="Load Profile", command=self.load_profile).pack(side="left", expand=True, fill="x", padx=(3, 0))

        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(fill="x", padx=10, pady=2)
        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=3)
        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x", padx=(3, 0))

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
        """Keyboard shortcuts for the points list (cross-platform)."""
        # Delete
        self.points_listbox.bind("<Delete>", lambda e: self.on_list_delete(e))
        self.root.bind("<Delete>", lambda e: self.on_list_delete(e))

        # Copy / Cut / Paste — Windows & Linux (Control) + macOS (Command)
        for mod in ("Control", "Command"):
            self.root.bind(f"<{mod}-c>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-C>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-x>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-X>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-v>", lambda e: self.on_list_paste(e))
            self.root.bind(f"<{mod}-V>", lambda e: self.on_list_paste(e))

    def on_list_delete(self, event=None):
        if self.is_focus_on_input() or self.is_running or self.is_recording:
            return
        if self.selected_index is not None:
            self.remove_point()
            return "break"

    def on_list_copy(self, event=None):
        if self.is_focus_on_input() or self.is_running or self.is_recording:
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        self.clipboard_point = copy.deepcopy(self.points[self.selected_index])
        self.status_label.config(text="Item copied", fg="#a6e3a1")
        return "break"

    def on_list_cut(self, event=None):
        if self.is_focus_on_input() or self.is_running or self.is_recording:
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        self.clipboard_point = copy.deepcopy(self.points[self.selected_index])
        del self.points[self.selected_index]
        self.selected_index = None
        self.edit_btn.config(state="disabled")
        self.refresh_points_list()
        self.status_label.config(text="Item cut", fg="#f9e2af")
        return "break"

    def on_list_paste(self, event=None):
        if self.is_focus_on_input() or self.is_running or self.is_recording:
            return
        if self.clipboard_point is None:
            self.status_label.config(text="Clipboard empty", fg="#f38ba8")
            return "break"
        new_item = copy.deepcopy(self.clipboard_point)
        # Insert after the currently selected item (or at end if nothing selected)
        if self.selected_index is not None and 0 <= self.selected_index < len(self.points):
            insert_at = self.selected_index + 1
        else:
            insert_at = len(self.points)
        self.points.insert(insert_at, new_item)
        self.refresh_points_list()
        self.selected_index = insert_at
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(insert_at)
        self.points_listbox.activate(insert_at)
        self.points_listbox.see(insert_at)
        self.edit_btn.config(state="normal")
        self.status_label.config(text="Item pasted", fg="#a6e3a1")
        return "break"

    def on_default_type_change(self, event=None):
        if self.pt_type_var.get() == "Double":
            self.pt_hold_spin.config(state="disabled")
        else:
            self.pt_hold_spin.config(state="normal")

    def set_record_indicator(self, active):
        color = "#ef4444" if active else "#5c1a1a"
        self.record_indicator.itemconfig("dot", fill=color)

    def on_list_drag_start(self, event):
        if self.is_running or self.is_recording:
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
        if self.is_running or self.is_recording or self.drag_start_index is None:
            return
        new_index = self.points_listbox.nearest(event.y)
        if new_index == self.drag_current_index:
            return
        if not (0 <= new_index < len(self.points)):
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

    def get_current_defaults(self):
        return {
            "hold": self.get_safe_int(self.pt_hold_var, 50, 10, 2000),
            "count": self.get_safe_int(self.pt_count_var, 1, 1, 100),
            "delay_after": self.get_safe_int(self.pt_delay_var, 100, 0, 10000),
            "type": self.pt_type_var.get()
        }

    def on_point_select(self, event=None):
        if self.is_running or self.is_recording:
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
                prefix += f"[{name}] "

            action = p.get("action")
            if action == "drag":
                text = f"{prefix}DRAG ({p['x']},{p['y']}) → ({p['drag_x']},{p['drag_y']}) x{p.get('count', 1)}"
            elif action == "wait":
                text = f"{prefix}WAIT {p.get('delay', 500)}ms"
            elif action == "key":
                text = f"{prefix}KEY '{p.get('key', '?')}' x{p.get('count', 1)}"
            elif action == "scroll":
                direction = "UP" if p.get("dy", 0) > 0 else "DOWN"
                if p.get("dx", 0) != 0:
                    direction = "RIGHT" if p.get("dx", 0) > 0 else "LEFT"
                text = f"{prefix}SCROLL {direction} ({p.get('x', 0)},{p.get('y', 0)}) x{p.get('count', 1)}"
            else:
                text = f"{prefix}CLICK ({p['x']},{p['y']}) {p.get('type', 'Left')} x{p.get('count', 1)}"
            self.points_listbox.insert(tk.END, text)

    def clear_previews(self):
        for w in self.preview_windows:
            try:
                w.destroy()
            except Exception:
                pass
        self.preview_windows.clear()

    def show_point_preview(self, x, y, color="#f38ba8", label=""):
        try:
            preview = tk.Toplevel(self.root)
            preview.overrideredirect(True)
            preview.attributes("-topmost", True)
            size = 28
            preview.geometry(f"{size}x{size}+{int(x) - size // 2}+{int(y) - size // 2}")
            canvas = tk.Canvas(preview, width=size, height=size, bg="#1e1e2e",
                               highlightthickness=0, bd=0)
            canvas.pack()
            canvas.create_oval(3, 3, size - 3, size - 3, outline=color, width=3)
            canvas.create_oval(size // 2 - 3, size // 2 - 3, size // 2 + 3, size // 2 + 3, fill=color, outline="")
            if label:
                canvas.create_text(size // 2, size // 2, text=label, fill="white", font=("Segoe UI", 7, "bold"))
            self.preview_windows.append(preview)
            return preview
        except Exception:
            return None

    def _move_preview(self, preview_win, x_var, y_var):
        """Live-update a preview window position from IntVars."""
        if preview_win is None:
            return
        try:
            x = int(x_var.get())
            y = int(y_var.get())
            size = 28
            preview_win.geometry(f"{size}x{size}+{x - size // 2}+{y - size // 2}")
        except Exception:
            pass

    def open_edit_popup(self):
        if self.is_running or self.is_recording or self.selected_index is None or self.selected_index >= len(self.points):
            return
        p = self.points[self.selected_index]
        action = p.get("action", "click")

        self.clear_previews()
        preview_main = None
        preview_end = None
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
        popup.grab_set()

        def on_popup_close():
            self.clear_previews()
            popup.destroy()

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)

        vcmd = (popup.register(self.validate_number), "%d", "%P")

        tk.Label(popup, text=f"Editing item #{self.selected_index + 1}", font=("Segoe UI", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 6))

        name_frame = tk.Frame(popup, bg="#1e1e2e")
        name_frame.pack(fill="x", padx=15, pady=(0, 6))
        tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        name_var = tk.StringVar(value=p.get("name", ""))
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=22)
        name_entry.pack(side="left", padx=(6, 0))

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

        if action == "wait":
            tk.Label(frame, text="Wait Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=p.get("delay", 500))
            ttk.Spinbox(frame, from_=1, to=60000, textvariable=var, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=3, padx=5)
            entries["delay"] = var

        elif action == "key":
            tk.Label(frame, text="Key:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
            key_var = tk.StringVar(value=p.get("key", "a"))
            ttk.Entry(frame, textvariable=key_var, width=12).grid(row=0, column=1, pady=2, padx=5)
            entries["key"] = key_var
            tk.Label(frame, text="(letter / f1-f12 / space / enter / ...)", bg="#1e1e2e",
                     fg="#6c7086", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=2, sticky="w")
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
            tk.Label(frame, text="dx (horizontal):", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            var_dx = tk.IntVar(value=p.get("dx", 0))
            ttk.Spinbox(frame, from_=-20, to=20, textvariable=var_dx, width=10,
                        validate="key", validatecommand=vcmd).grid(row=2, column=1, pady=2, padx=5)
            entries["dx"] = var_dx
            tk.Label(frame, text="dy (vertical):", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
            var_dy = tk.IntVar(value=p.get("dy", 0))
            ttk.Spinbox(frame, from_=-20, to=20, textvariable=var_dy, width=10,
                        validate="key", validatecommand=vcmd).grid(row=3, column=1, pady=2, padx=5)
            entries["dy"] = var_dy
            tk.Label(frame, text="(+dy = UP, -dy = DOWN)", bg="#1e1e2e",
                     fg="#6c7086", font=("Segoe UI", 8)).grid(row=4, column=0, columnspan=2, sticky="w")
            tk.Label(frame, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
            var_count = tk.IntVar(value=p.get("count", 1))
            ttk.Spinbox(frame, from_=1, to=100, textvariable=var_count, width=10,
                        validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)
            entries["count"] = var_count
            tk.Label(frame, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=6, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=p.get("delay_after", 50))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=6, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        elif action == "drag":
            labels = [
                ("Start X:", "x"), ("Start Y:", "y"),
                ("End X:", "drag_x"), ("End Y:", "drag_y"),
                ("Duration (ms):", "hold"),
                ("Repeat:", "count"),
                ("Delay Between Repeats (ms):", "delay_after")
            ]
            for i, (label, key) in enumerate(labels):
                tk.Label(frame, text=label, bg="#1e1e2e", fg="#cdd6f4").grid(row=i, column=0, sticky="w", pady=2)
                default_val = p.get(key, 1 if key == "count" else 0)
                var = tk.IntVar(value=default_val)
                max_val = 100 if key == "count" else (99999 if key in ("hold", "delay_after") else 10000)
                from_val = 1 if key == "count" else 0
                ttk.Spinbox(frame, from_=from_val, to=max_val,
                            textvariable=var, width=10, validate="key", validatecommand=vcmd).grid(row=i, column=1, pady=2, padx=5)
                entries[key] = var
            bind_live_preview(entries["x"], entries["y"], preview_main)
            bind_live_preview(entries["drag_x"], entries["drag_y"], preview_end)

        else:  # click
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
                if var_type.get() == "Double":
                    hold_spin.config(state="disabled")
                else:
                    hold_spin.config(state="normal")

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
                    p["dx"] = int(entries["dx"].get())
                    p["dy"] = int(entries["dy"].get())
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
                self.points_listbox.selection_set(self.selected_index)
                self.points_listbox.activate(self.selected_index)
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
        if self.is_running or self.is_recording:
            return
        delay = self.get_safe_int(self.pt_delay_var, 500, 1, 60000)
        point = {"action": "wait", "delay": delay, "name": ""}
        self.points.append(point)
        self.refresh_points_list()
        self.status_label.config(text=f"Wait {delay}ms added", fg="#a6e3a1")

    def add_key_action(self):
        if self.is_running or self.is_recording:
            return
        popup = tk.Toplevel(self.root)
        popup.title("Add Keyboard Action")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        tk.Label(popup, text="Press a key or type its name", font=("Segoe UI", 10, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 6))
        tk.Label(popup, text="(letters, f1-f12, space, enter, tab, esc, ...)",
                 bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()

        key_var = tk.StringVar(value="")
        entry = ttk.Entry(popup, textvariable=key_var, width=18, font=("Segoe UI", 11))
        entry.pack(pady=8)
        entry.focus_set()

        def capture_from_listener():
            self.status_label.config(text="Press any key to capture...", fg="#f9e2af")

            def on_press(key):
                try:
                    kstr = key_to_str(key)
                    if kstr:
                        self.root.after(0, lambda: key_var.set(kstr))
                        return False
                except Exception:
                    pass
                return True

            listener = KeyboardListener(on_press=on_press)
            listener.start()

        def apply():
            k = key_var.get().strip().lower()
            if not k:
                messagebox.showwarning("Warning", "Enter or capture a key.", parent=popup)
                return
            defaults = self.get_current_defaults()
            point = {
                "action": "key",
                "key": k,
                "count": defaults["count"],
                "delay_after": defaults["delay_after"],
                "name": ""
            }
            self.points.append(point)
            self.refresh_points_list()
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
        if self.is_running or self.is_recording:
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
        if mode == "click":
            self.status_label.config(text="Click to add a new CLICK point...", fg="#f9e2af")
        else:
            self.status_label.config(text="Press & hold, then release to set DRAG...", fg="#f9e2af")

        def on_click(x, y, button, pressed):
            if button != Button.left:
                return
            defaults = self.get_current_defaults()
            if self.adding_mode == "click":
                if pressed:
                    point = {"action": "click", "x": x, "y": y, "name": "", **defaults}
                    self.points.append(point)
                    self.root.after(0, self.finish_add_point, f"Click point added ({x},{y})")
                    return False
            elif self.adding_mode == "drag":
                if pressed:
                    self.temp_drag_start = (x, y)
                    self.adding_mode = "drag_release"
                    return True
            elif self.adding_mode == "drag_release":
                if not pressed and self.temp_drag_start is not None:
                    point = {
                        "action": "drag",
                        "x": self.temp_drag_start[0],
                        "y": self.temp_drag_start[1],
                        "drag_x": x,
                        "drag_y": y,
                        "hold": defaults["hold"],
                        "count": defaults["count"],
                        "delay_after": defaults["delay_after"],
                        "type": "Left",
                        "name": ""
                    }
                    self.points.append(point)
                    self.root.after(0, self.finish_add_point, "Drag point added")
                    return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def finish_add_point(self, message):
        self.adding_mode = None
        self.temp_drag_start = None
        if self.click_listener:
            try:
                if self.click_listener.is_alive():
                    self.click_listener.stop()
            except Exception:
                pass
            self.click_listener = None
        self.refresh_points_list()
        self.restore_after_capture()
        self.status_label.config(text=message, fg="#a6e3a1")

    def toggle_recording(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Stop the running sequence first.")
            return
        if self.is_recording:
            self.stop_recording(from_ui=True)
        else:
            self.start_recording()

    def start_recording(self):
        self.is_recording = True
        self.record_events = []
        self.record_start_time = time.time()
        self.record_btn.config(text="Stop Rec")
        self.set_record_indicator(True)
        self.status_label.config(text=f"Recording... Press {self.record_stop_hotkey.upper()} to stop", fg="#f38ba8")
        self.minimize_for_capture()

        if self.record_mouse_listener and self.record_mouse_listener.is_alive():
            try:
                self.record_mouse_listener.stop()
            except Exception:
                pass
        if self.record_keyboard_listener and self.record_keyboard_listener.is_alive():
            try:
                self.record_keyboard_listener.stop()
            except Exception:
                pass

        self._rec_drag_start = None
        self._rec_last_time = self.record_start_time

        def on_click(x, y, button, pressed):
            if not self.is_recording:
                return False
            now = time.time()
            delay_ms = int((now - self._rec_last_time) * 1000)
            self._rec_last_time = now

            btn_name = "Left"
            if button == Button.right:
                btn_name = "Right"
            elif button == Button.middle:
                btn_name = "Middle"

            if pressed:
                self._rec_drag_start = (x, y, btn_name, delay_ms)
            else:
                if self._rec_drag_start:
                    sx, sy, bname, dly = self._rec_drag_start
                    if abs(x - sx) > 5 or abs(y - sy) > 5:
                        if dly > 30:
                            self.record_events.append({"action": "wait", "delay": dly, "name": ""})
                        self.record_events.append({
                            "action": "drag",
                            "x": sx, "y": sy,
                            "drag_x": x, "drag_y": y,
                            "hold": max(50, int((now - self.record_start_time) * 10) % 500 + 100),
                            "count": 1,
                            "delay_after": 50,
                            "type": "Left",
                            "name": ""
                        })
                    else:
                        if dly > 30:
                            self.record_events.append({"action": "wait", "delay": dly, "name": ""})
                        self.record_events.append({
                            "action": "click",
                            "x": sx, "y": sy,
                            "hold": 50,
                            "count": 1,
                            "delay_after": 50,
                            "type": bname,
                            "name": ""
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
            self.record_events.append({
                "action": "scroll",
                "x": x, "y": y,
                "dx": int(dx), "dy": int(dy),
                "count": 1,
                "delay_after": 30,
                "name": ""
            })
            return True

        def on_press(key):
            if not self.is_recording:
                return False
            kstr = key_to_str(key)
            if kstr == self.record_stop_hotkey:
                return True
            now = time.time()
            delay_ms = int((now - self._rec_last_time) * 1000)
            self._rec_last_time = now
            if delay_ms > 30:
                self.record_events.append({"action": "wait", "delay": delay_ms, "name": ""})
            self.record_events.append({
                "action": "key",
                "key": kstr,
                "count": 1,
                "delay_after": 50,
                "name": ""
            })
            return True

        self.record_mouse_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
        self.record_mouse_listener.start()
        self.record_keyboard_listener = KeyboardListener(on_press=on_press)
        self.record_keyboard_listener.start()

    def stop_recording(self, from_ui=False):
        self.is_recording = False
        if self.record_mouse_listener:
            try:
                if self.record_mouse_listener.is_alive():
                    self.record_mouse_listener.stop()
            except Exception:
                pass
            self.record_mouse_listener = None
        if self.record_keyboard_listener:
            try:
                if self.record_keyboard_listener.is_alive():
                    self.record_keyboard_listener.stop()
            except Exception:
                pass
            self.record_keyboard_listener = None

        if from_ui and self.record_events:
            last = self.record_events[-1]
            if last.get("action") == "click":
                self.record_events.pop()
                if self.record_events and self.record_events[-1].get("action") == "wait":
                    self.record_events.pop()

        count_before = len(self.points)
        self.points.extend(self.record_events)
        added = len(self.points) - count_before
        self.record_events = []
        self.refresh_points_list()
        self.restore_after_capture()
        self.record_btn.config(text="Record")
        self.set_record_indicator(False)
        self.status_label.config(text=f"Recording stopped — {added} actions added", fg="#a6e3a1")

    def move_up(self):
        if self.selected_index is None or self.selected_index == 0 or self.is_running or self.is_recording:
            return
        i = self.selected_index
        self.points[i], self.points[i - 1] = self.points[i - 1], self.points[i]
        self.selected_index = i - 1
        self.refresh_points_list()
        self.points_listbox.selection_set(self.selected_index)
        self.edit_btn.config(state="normal")

    def move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.points) - 1 or self.is_running or self.is_recording:
            return
        i = self.selected_index
        self.points[i], self.points[i + 1] = self.points[i + 1], self.points[i]
        self.selected_index = i + 1
        self.refresh_points_list()
        self.points_listbox.selection_set(self.selected_index)
        self.edit_btn.config(state="normal")

    def remove_point(self):
        if self.is_running or self.is_recording or self.selected_index is None:
            return
        del self.points[self.selected_index]
        self.selected_index = None
        self.edit_btn.config(state="disabled")
        self.refresh_points_list()
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_running or self.is_recording:
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
        label = {"start": "START", "stop": "STOP", "record_stop": "STOP RECORD"}.get(which, which.upper())
        self.status_label.config(text=f"Press a key for {label}...", fg="#f9e2af")

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                kstr = key_to_str(key)

                if self.waiting_for_hotkey:
                    if key == Key.esc:
                        self.waiting_for_hotkey = None
                        self.status_label.config(text="Cancelled", fg="#f9e2af")
                        return

                    if not kstr:
                        return

                    all_hk = {
                        "start": self.start_hotkey,
                        "stop": self.stop_hotkey,
                        "record_stop": self.record_stop_hotkey
                    }
                    for name, val in all_hk.items():
                        if name != self.waiting_for_hotkey and val == kstr:
                            self.status_label.config(text="Same key not allowed!", fg="#f38ba8")
                            self.waiting_for_hotkey = None
                            return

                    if self.waiting_for_hotkey == "start":
                        self.start_hotkey = kstr
                        self.start_hk_label.config(text=f"Start Hotkey: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "stop":
                        self.stop_hotkey = kstr
                        self.stop_hk_label.config(text=f"Stop Hotkey: {kstr.upper()}")
                    elif self.waiting_for_hotkey == "record_stop":
                        self.record_stop_hotkey = kstr
                        self.record_stop_hk_label.config(text=f"Stop Record: {kstr.upper()}")

                    self.status_label.config(text=f"Hotkey → {kstr.upper()}", fg="#a6e3a1")
                    self.waiting_for_hotkey = None
                    return

                if self.is_focus_on_input():
                    return

                if self.is_recording and kstr == self.record_stop_hotkey:
                    self.root.after(0, lambda: self.stop_recording(from_ui=False))
                    return

                if self.g_hotkey_enabled.get() and kstr == self.start_hotkey and not self.is_running and not self.is_recording:
                    self.root.after(0, self.start_clicking)
                if self.s_hotkey_enabled.get() and kstr == self.stop_hotkey and self.is_running:
                    self.root.after(0, self.stop_clicking)

            except Exception:
                pass

        self.keyboard_listener = KeyboardListener(on_press=on_press)
        self.keyboard_listener.start()

    def get_safe_int(self, var, default, min_val=0, max_val=999999):
        try:
            value = int(var.get())
            return max(min_val, min(value, max_val))
        except Exception:
            return default

    def start_clicking(self):
        if not self.points:
            messagebox.showwarning("Warning", "Add at least one point!")
            return
        if self.is_running or self.is_recording:
            return
        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.record_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")
        self.progress_label.config(text="")

        random_ms = self.get_safe_int(self.random_var, 0, 0, 500)
        pos_rand = self.get_safe_int(self.pos_random_var, 0, 0, 50)
        cycles = self.get_safe_int(self.rep_var, 1, 1, 99999)
        thread = threading.Thread(target=self.click_loop, args=(random_ms, pos_rand, cycles), daemon=True)
        thread.start()

    def apply_pos_random(self, x, y, pos_rand):
        if pos_rand <= 0:
            return x, y
        rx = random.randint(-pos_rand, pos_rand)
        ry = random.randint(-pos_rand, pos_rand)
        return x + rx, y + ry

    def perform_click(self, p, pos_rand):
        x, y = self.apply_pos_random(p["x"], p["y"], pos_rand)
        hold = p.get("hold", 50)
        typ = p.get("type", "Left")
        btn = {"Left": Button.left, "Right": Button.right, "Middle": Button.middle}.get(typ, Button.left)
        self.mouse.position = (x, y)
        if typ == "Double":
            self.mouse.click(btn, 2)
        else:
            self.mouse.press(btn)
            time.sleep(hold / 1000.0)
            self.mouse.release(btn)

    def perform_drag(self, p, pos_rand):
        sx, sy = self.apply_pos_random(p["x"], p["y"], pos_rand)
        ex, ey = self.apply_pos_random(p["drag_x"], p["drag_y"], pos_rand)
        duration = p.get("hold", 300) / 1000.0
        self.mouse.position = (sx, sy)
        self.mouse.press(Button.left)
        steps = max(8, int(duration * 50))
        for i in range(1, steps + 1):
            if self.stop_flag:
                break
            t = i / steps
            cx = int(sx + (ex - sx) * t)
            cy = int(sy + (ey - sy) * t)
            self.mouse.position = (cx, cy)
            time.sleep(duration / steps)
        self.mouse.release(Button.left)

    def perform_key(self, p):
        k = p.get("key", "a")
        key_obj = str_to_key(k)
        try:
            self.keyboard.press(key_obj)
            self.keyboard.release(key_obj)
        except Exception:
            try:
                self.keyboard.press(k)
                self.keyboard.release(k)
            except Exception:
                pass

    def perform_scroll(self, p, pos_rand):
        x, y = self.apply_pos_random(p.get("x", 0), p.get("y", 0), pos_rand)
        self.mouse.position = (x, y)
        dx = p.get("dx", 0)
        dy = p.get("dy", 0)
        self.mouse.scroll(dx, dy)

    def click_loop(self, random_ms, pos_rand, max_cycles):
        cycle = 0
        total_points = len(self.points)
        if self.infinite.get():
            max_cycles = float("inf")

        while not self.stop_flag and cycle < max_cycles:
            for idx, p in enumerate(self.points):
                if self.stop_flag:
                    break
                self.root.after(0, self.highlight_current, idx)

                if self.infinite.get():
                    prog_text = f"Cycle {cycle + 1} (∞)  |  Step {idx + 1}/{total_points}"
                else:
                    pct = int(((cycle * total_points + idx) / (max_cycles * total_points)) * 100) if max_cycles * total_points > 0 else 0
                    prog_text = f"Cycle {cycle + 1}/{max_cycles}  |  Step {idx + 1}/{total_points}  |  {pct}%"
                self.root.after(0, lambda t=prog_text: self.progress_label.config(text=t))

                action = p.get("action")
                if action == "wait":
                    delay = p.get("delay", 500)
                    if random_ms > 0:
                        delay += random.randint(-random_ms, random_ms)
                    delay = max(0, delay)
                    time.sleep(delay / 1000.0)
                    continue

                count = p.get("count", 1)
                delay_between = p.get("delay_after", 0)

                if action == "drag":
                    for i in range(count):
                        if self.stop_flag:
                            break
                        self.perform_drag(p, pos_rand)
                        if i < count - 1 and delay_between > 0:
                            d = delay_between
                            if random_ms > 0:
                                d += random.randint(-random_ms, random_ms)
                            time.sleep(max(0, d) / 1000.0)
                elif action == "key":
                    for i in range(count):
                        if self.stop_flag:
                            break
                        self.perform_key(p)
                        if i < count - 1 and delay_between > 0:
                            d = delay_between
                            if random_ms > 0:
                                d += random.randint(-random_ms, random_ms)
                            time.sleep(max(0, d) / 1000.0)
                elif action == "scroll":
                    for i in range(count):
                        if self.stop_flag:
                            break
                        self.perform_scroll(p, pos_rand)
                        if i < count - 1 and delay_between > 0:
                            d = delay_between
                            if random_ms > 0:
                                d += random.randint(-random_ms, random_ms)
                            time.sleep(max(0, d) / 1000.0)
                else:
                    for i in range(count):
                        if self.stop_flag:
                            break
                        self.perform_click(p, pos_rand)
                        if i < count - 1 and delay_between > 0:
                            d = delay_between
                            if random_ms > 0:
                                d += random.randint(-random_ms, random_ms)
                            time.sleep(max(0, d) / 1000.0)
            cycle += 1

        self.is_running = False
        self.root.after(0, self.on_clicking_finished)

    def on_clicking_finished(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.record_btn.config(state="normal")
        self.clear_highlight()
        if self.selected_index is not None:
            self.edit_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")
        self.progress_label.config(text="")

    def stop_clicking(self):
        self.stop_flag = True
        self.status_label.config(text="Stopping...", fg="#f9e2af")

    def save_profile(self):
        data = {
            "points": self.points,
            "random": self.random_var.get(),
            "pos_random": self.pos_random_var.get(),
            "cycles": self.rep_var.get(),
            "infinite": self.infinite.get(),
            "start_hotkey": self.start_hotkey,
            "stop_hotkey": self.stop_hotkey,
            "record_stop_hotkey": self.record_stop_hotkey,
            "start_enabled": self.g_hotkey_enabled.get(),
            "stop_enabled": self.s_hotkey_enabled.get(),
            "always_on_top": self.always_on_top.get(),
            "defaults": self.get_current_defaults()
        }
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON Profile", "*.json")])
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
                if "name" not in p:
                    p["name"] = ""
            self.refresh_points_list()
            self.random_var.set(data.get("random", 0))
            self.pos_random_var.set(data.get("pos_random", 0))
            self.rep_var.set(data.get("cycles", 1))
            self.infinite.set(data.get("infinite", False))
            self.toggle_infinite()
            self.start_hotkey = data.get("start_hotkey", "f1")
            self.stop_hotkey = data.get("stop_hotkey", "f2")
            self.record_stop_hotkey = data.get("record_stop_hotkey", "f3")
            self.start_hk_label.config(text=f"Start Hotkey: {self.start_hotkey.upper()}")
            self.stop_hk_label.config(text=f"Stop Hotkey: {self.stop_hotkey.upper()}")
            self.record_stop_hk_label.config(text=f"Stop Record: {self.record_stop_hotkey.upper()}")
            self.g_hotkey_enabled.set(data.get("start_enabled", True))
            self.s_hotkey_enabled.set(data.get("stop_enabled", True))
            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_topmost()
            defaults = data.get("defaults", {})
            self.pt_hold_var.set(defaults.get("hold", 50))
            self.pt_count_var.set(defaults.get("count", 1))
            self.pt_delay_var.set(defaults.get("delay_after", 100))
            typ = defaults.get("type", "Left")
            self.pt_type_var.set(typ)
            self.pt_type_combo.set(typ)
            self.on_default_type_change()
            self.selected_index = None
            self.edit_btn.config(state="disabled")
            self.status_label.config(text="Profile loaded", fg="#a6e3a1")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exit_app(self):
        self.stop_flag = True
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
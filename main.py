import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import random
import ctypes
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Listener as KeyboardListener

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.geometry("480x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.version = "v2.1"

        # State
        self.points = []  # list of dicts
        self.selected_index = None
        self.is_running = False
        self.stop_flag = False
        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)

        self.start_hotkey = "g"
        self.stop_hotkey = "s"

        self.mouse = MouseController()
        self.click_listener = None
        self.keyboard_listener = None
        self.waiting_for_hotkey = None
        self.adding_mode = None  # "click" or "drag_start" or "drag_end"

        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())

        self.setup_ui()
        self.start_keyboard_listener()

    def force_english_keyboard(self):
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
        style.configure("TButton", padding=4, font=("Segoe UI", 9))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 9))
        style.configure("TCombobox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TSpinbox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TLabelframe", background="#1e1e2e", foreground="#89b4fa")
        style.configure("TLabelframe.Label", background="#1e1e2e", foreground="#89b4fa", font=("Segoe UI", 9, "bold"))

        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        # Title
        tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 16, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(8, 4))

        # ========== Points Section ==========
        points_frame = ttk.LabelFrame(self.root, text=" Points (Sequence) ", padding=6)
        points_frame.pack(fill="x", padx=12, pady=3)

        list_frame = tk.Frame(points_frame, bg="#1e1e2e")
        list_frame.pack(fill="x")

        self.points_listbox = tk.Listbox(list_frame, height=4, bg="#313244", fg="#cdd6f4",
                                         selectbackground="#89b4fa", font=("Consolas", 9),
                                         relief="flat", highlightthickness=0)
        self.points_listbox.pack(side="left", fill="x", expand=True)
        self.points_listbox.bind("<<ListboxSelect>>", self.on_point_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.points_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.points_listbox.config(yscrollcommand=scrollbar.set)

        btn_row = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(4, 0))

        self.add_click_btn = ttk.Button(btn_row, text="Add Click", command=lambda: self.start_add_point("click"))
        self.add_click_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))

        self.add_drag_btn = ttk.Button(btn_row, text="Add Drag", command=lambda: self.start_add_point("drag"))
        self.add_drag_btn.pack(side="left", expand=True, fill="x", padx=3)

        self.remove_btn = ttk.Button(btn_row, text="Remove", command=self.remove_point)
        self.remove_btn.pack(side="left", expand=True, fill="x", padx=3)

        self.clear_btn = ttk.Button(btn_row, text="Clear", command=self.clear_points)
        self.clear_btn.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # ========== Selected Point Settings ==========
        self.point_settings_frame = ttk.LabelFrame(self.root, text=" Selected Point Settings ", padding=6)
        self.point_settings_frame.pack(fill="x", padx=12, pady=3)

        # Hold
        row1 = tk.Frame(self.point_settings_frame, bg="#1e1e2e")
        row1.pack(fill="x", pady=1)
        tk.Label(row1, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4", width=12, anchor="w").pack(side="left")
        self.pt_hold_var = tk.IntVar(value=50)
        self.pt_hold_spin = ttk.Spinbox(row1, from_=10, to=2000, textvariable=self.pt_hold_var, width=8,
                                        validate="key", validatecommand=vcmd, command=self.apply_point_settings)
        self.pt_hold_spin.pack(side="left")
        self.pt_hold_spin.bind("<FocusOut>", lambda e: self.apply_point_settings())

        # Count at this point
        tk.Label(row1, text="  Clicks:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(8, 0))
        self.pt_count_var = tk.IntVar(value=1)
        self.pt_count_spin = ttk.Spinbox(row1, from_=1, to=100, textvariable=self.pt_count_var, width=6,
                                         validate="key", validatecommand=vcmd, command=self.apply_point_settings)
        self.pt_count_spin.pack(side="left")
        self.pt_count_spin.bind("<FocusOut>", lambda e: self.apply_point_settings())

        # Delay after
        row2 = tk.Frame(self.point_settings_frame, bg="#1e1e2e")
        row2.pack(fill="x", pady=1)
        tk.Label(row2, text="Delay After (ms):", bg="#1e1e2e", fg="#cdd6f4", width=12, anchor="w").pack(side="left")
        self.pt_delay_var = tk.IntVar(value=100)
        self.pt_delay_spin = ttk.Spinbox(row2, from_=0, to=10000, textvariable=self.pt_delay_var, width=8,
                                         validate="key", validatecommand=vcmd, command=self.apply_point_settings)
        self.pt_delay_spin.pack(side="left")
        self.pt_delay_spin.bind("<FocusOut>", lambda e: self.apply_point_settings())

        # Click type for this point
        tk.Label(row2, text="  Type:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(8, 0))
        self.pt_type_var = tk.StringVar(value="Left")
        self.pt_type_combo = ttk.Combobox(row2, textvariable=self.pt_type_var,
                                          values=["Left", "Right", "Double", "Middle"],
                                          state="readonly", width=8)
        self.pt_type_combo.pack(side="left")
        self.pt_type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_point_settings())

        # ========== Global Settings ==========
        global_frame = ttk.LabelFrame(self.root, text=" Global Settings ", padding=6)
        global_frame.pack(fill="x", padx=12, pady=3)

        rowg1 = tk.Frame(global_frame, bg="#1e1e2e")
        rowg1.pack(fill="x", pady=1)
        tk.Label(rowg1, text="Random ± (ms):", bg="#1e1e2e", fg="#cdd6f4", width=14, anchor="w").pack(side="left")
        self.random_var = tk.IntVar(value=0)
        ttk.Spinbox(rowg1, from_=0, to=500, textvariable=self.random_var, width=8,
                    validate="key", validatecommand=vcmd).pack(side="left")

        tk.Label(rowg1, text="  Total Cycles:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(10, 0))
        self.rep_var = tk.IntVar(value=1)
        self.rep_spin = ttk.Spinbox(rowg1, from_=1, to=99999, textvariable=self.rep_var, width=6,
                                    validate="key", validatecommand=vcmd)
        self.rep_spin.pack(side="left")
        ttk.Checkbutton(rowg1, text="Infinite", variable=self.infinite,
                        command=self.toggle_infinite).pack(side="left", padx=6)

        rowg2 = tk.Frame(global_frame, bg="#1e1e2e")
        rowg2.pack(fill="x", pady=2)
        ttk.Checkbutton(rowg2, text="Always on Top", variable=self.always_on_top,
                        command=self.toggle_topmost).pack(side="left")

        # ========== Hotkeys ==========
        hotkey_frame = ttk.LabelFrame(self.root, text=" Hotkeys ", padding=6)
        hotkey_frame.pack(fill="x", padx=12, pady=3)

        hk1 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk1.pack(fill="x", pady=1)
        self.start_hk_label = tk.Label(hk1, text=f"Start: {self.start_hotkey.upper()}",
                                       bg="#1e1e2e", fg="#cdd6f4", width=12, anchor="w")
        self.start_hk_label.pack(side="left")
        ttk.Button(hk1, text="Change", width=7, command=lambda: self.change_hotkey("start")).pack(side="left", padx=3)
        ttk.Checkbutton(hk1, text="Enable", variable=self.g_hotkey_enabled).pack(side="left")

        hk2 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk2.pack(fill="x", pady=1)
        self.stop_hk_label = tk.Label(hk2, text=f"Stop:  {self.stop_hotkey.upper()}",
                                      bg="#1e1e2e", fg="#cdd6f4", width=12, anchor="w")
        self.stop_hk_label.pack(side="left")
        ttk.Button(hk2, text="Change", width=7, command=lambda: self.change_hotkey("stop")).pack(side="left", padx=3)
        ttk.Checkbutton(hk2, text="Enable", variable=self.s_hotkey_enabled).pack(side="left")

        # ========== Profile + Actions ==========
        profile_frame = tk.Frame(self.root, bg="#1e1e2e")
        profile_frame.pack(fill="x", padx=12, pady=4)
        ttk.Button(profile_frame, text="Save Profile", command=self.save_profile).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(profile_frame, text="Load Profile", command=self.load_profile).pack(side="left", expand=True, fill="x", padx=(3, 0))

        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(fill="x", padx=12, pady=2)
        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 3))
        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=3)
        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x", padx=(3, 0))

        # Status
        bottom = tk.Frame(self.root, bg="#1e1e2e")
        bottom.pack(side="bottom", fill="x", padx=12, pady=6)
        self.status_label = tk.Label(bottom, text="Ready", font=("Segoe UI", 9),
                                     bg="#1e1e2e", fg="#f9e2af")
        self.status_label.pack(side="left")
        tk.Label(bottom, text=self.version, font=("Segoe UI", 8),
                 bg="#1e1e2e", fg="#6c7086").pack(side="right")

        self.disable_point_settings()

    def disable_point_settings(self):
        for w in (self.pt_hold_spin, self.pt_count_spin, self.pt_delay_spin, self.pt_type_combo):
            w.config(state="disabled")

    def enable_point_settings(self):
        for w in (self.pt_hold_spin, self.pt_count_spin, self.pt_delay_spin, self.pt_type_combo):
            w.config(state="normal")
        self.pt_type_combo.config(state="readonly")

    def on_point_select(self, event=None):
        sel = self.points_listbox.curselection()
        if not sel:
            self.selected_index = None
            self.disable_point_settings()
            return
        self.selected_index = sel[0]
        p = self.points[self.selected_index]
        self.pt_hold_var.set(p.get("hold", 50))
        self.pt_count_var.set(p.get("count", 1))
        self.pt_delay_var.set(p.get("delay_after", 100))
        self.pt_type_var.set(p.get("type", "Left"))
        self.enable_point_settings()

    def apply_point_settings(self):
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        p = self.points[self.selected_index]
        p["hold"] = self.get_safe_int(self.pt_hold_var, 50, 10, 2000)
        p["count"] = self.get_safe_int(self.pt_count_var, 1, 1, 100)
        p["delay_after"] = self.get_safe_int(self.pt_delay_var, 100, 0, 10000)
        p["type"] = self.pt_type_var.get()
        self.refresh_points_list()
        # re-select
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(self.selected_index)
        self.points_listbox.activate(self.selected_index)

    def refresh_points_list(self):
        self.points_listbox.delete(0, tk.END)
        for i, p in enumerate(self.points, 1):
            if p.get("action") == "drag":
                text = f"{i}. DRAG ({p['x']},{p['y']}) → ({p['drag_x']},{p['drag_y']})"
            else:
                text = f"{i}. ({p['x']},{p['y']}) {p.get('type','Left')} x{p.get('count',1)}"
            self.points_listbox.insert(tk.END, text)

    def start_add_point(self, mode):
        if self.is_running:
            return
        self.adding_mode = mode
        if mode == "click":
            self.status_label.config(text="Click to add a CLICK point...", fg="#f9e2af")
        else:
            self.status_label.config(text="Click START position of DRAG...", fg="#f9e2af")
        self.add_click_btn.config(state="disabled")
        self.add_drag_btn.config(state="disabled")

        def on_click(x, y, button, pressed):
            if not pressed or button != Button.left:
                return
            if self.adding_mode == "click":
                point = {
                    "action": "click",
                    "x": x, "y": y,
                    "hold": 50,
                    "count": 1,
                    "delay_after": 100,
                    "type": "Left"
                }
                self.points.append(point)
                self.refresh_points_list()
                self.status_label.config(text=f"Click point added ({x},{y})", fg="#a6e3a1")
                self.finish_adding()
                return False

            elif self.adding_mode == "drag":
                self.temp_drag_start = (x, y)
                self.adding_mode = "drag_end"
                self.status_label.config(text="Now click END position of DRAG...", fg="#f9e2af")
                return True  # continue listening

            elif self.adding_mode == "drag_end":
                point = {
                    "action": "drag",
                    "x": self.temp_drag_start[0],
                    "y": self.temp_drag_start[1],
                    "drag_x": x,
                    "drag_y": y,
                    "hold": 300,          # drag duration
                    "count": 1,
                    "delay_after": 100,
                    "type": "Left"
                }
                self.points.append(point)
                self.refresh_points_list()
                self.status_label.config(text=f"Drag added ({self.temp_drag_start}) → ({x},{y})", fg="#a6e3a1")
                self.finish_adding()
                return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def finish_adding(self):
        self.adding_mode = None
        self.add_click_btn.config(state="normal")
        self.add_drag_btn.config(state="normal")

    def remove_point(self):
        if self.is_running:
            return
        sel = self.points_listbox.curselection()
        if not sel:
            return
        del self.points[sel[0]]
        self.selected_index = None
        self.refresh_points_list()
        self.disable_point_settings()
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_running:
            return
        self.points.clear()
        self.selected_index = None
        self.refresh_points_list()
        self.disable_point_settings()
        self.status_label.config(text="All points cleared", fg="#f9e2af")

    def toggle_infinite(self):
        self.rep_spin.config(state="disabled" if self.infinite.get() else "normal")

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    def change_hotkey(self, which):
        self.force_english_keyboard()
        self.waiting_for_hotkey = which
        self.status_label.config(text=f"Press English key for {which.upper()}...", fg="#f9e2af")

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                if self.waiting_for_hotkey:
                    char = None
                    if hasattr(key, "char") and key.char:
                        char = key.char.lower()
                    elif key == Key.esc:
                        self.waiting_for_hotkey = None
                        self.status_label.config(text="Cancelled", fg="#f9e2af")
                        return
                    if char and char.isascii() and char.isalpha():
                        if self.waiting_for_hotkey == "start":
                            if char == self.stop_hotkey:
                                self.status_label.config(text="Same key not allowed!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.start_hotkey = char
                            self.start_hk_label.config(text=f"Start: {char.upper()}")
                        else:
                            if char == self.start_hotkey:
                                self.status_label.config(text="Same key not allowed!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.stop_hotkey = char
                            self.stop_hk_label.config(text=f"Stop:  {char.upper()}")
                        self.status_label.config(text=f"Hotkey → {char.upper()}", fg="#a6e3a1")
                        self.waiting_for_hotkey = None
                    return

                if self.is_focus_on_input():
                    return

                if hasattr(key, "char") and key.char:
                    pressed = key.char.lower()
                    if self.g_hotkey_enabled.get() and pressed == self.start_hotkey and not self.is_running:
                        self.root.after(0, self.start_clicking)
                    if self.s_hotkey_enabled.get() and pressed == self.stop_hotkey and self.is_running:
                        self.root.after(0, self.stop_clicking)
            except AttributeError:
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
        if self.is_running:
            return

        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.add_click_btn.config(state="disabled")
        self.add_drag_btn.config(state="disabled")
        self.remove_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")

        random_ms = self.get_safe_int(self.random_var, 0, 0, 500)
        cycles = self.get_safe_int(self.rep_var, 1, 1, 99999)

        thread = threading.Thread(target=self.click_loop, args=(random_ms, cycles), daemon=True)
        thread.start()

    def perform_click(self, p):
        x, y = p["x"], p["y"]
        hold = p.get("hold", 50)
        typ = p.get("type", "Left")

        if typ == "Left":
            btn = Button.left
        elif typ == "Right":
            btn = Button.right
        elif typ == "Middle":
            btn = Button.middle
        else:
            btn = Button.left

        self.mouse.position = (x, y)

        if typ == "Double":
            self.mouse.click(btn, 2)
        else:
            self.mouse.press(btn)
            time.sleep(hold / 1000.0)
            self.mouse.release(btn)

    def perform_drag(self, p):
        start = (p["x"], p["y"])
        end = (p["drag_x"], p["drag_y"])
        duration = p.get("hold", 300) / 1000.0

        self.mouse.position = start
        self.mouse.press(Button.left)
        # simple linear move
        steps = max(10, int(duration * 60))
        for i in range(1, steps + 1):
            if self.stop_flag:
                break
            t = i / steps
            cx = int(start[0] + (end[0] - start[0]) * t)
            cy = int(start[1] + (end[1] - start[1]) * t)
            self.mouse.position = (cx, cy)
            time.sleep(duration / steps)
        self.mouse.release(Button.left)

    def click_loop(self, random_ms, max_cycles):
        cycle = 0
        if self.infinite.get():
            max_cycles = float("inf")

        while not self.stop_flag and cycle < max_cycles:
            for p in self.points:
                if self.stop_flag:
                    break

                if p.get("action") == "drag":
                    self.perform_drag(p)
                else:
                    count = p.get("count", 1)
                    for _ in range(count):
                        if self.stop_flag:
                            break
                        self.perform_click(p)
                        # small gap between multi-clicks on same point
                        if count > 1:
                            time.sleep(0.05)

                # delay after this point
                delay = p.get("delay_after", 100)
                if random_ms > 0:
                    delay += random.randint(-random_ms, random_ms)
                delay = max(0, delay)
                if delay > 0 and not self.stop_flag:
                    time.sleep(delay / 1000.0)

            cycle += 1

        self.is_running = False
        self.root.after(0, self.on_clicking_finished)

    def on_clicking_finished(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.add_click_btn.config(state="normal")
        self.add_drag_btn.config(state="normal")
        self.remove_btn.config(state="normal")
        self.clear_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")

    def stop_clicking(self):
        self.stop_flag = True
        self.status_label.config(text="Stopping...", fg="#f9e2af")

    def save_profile(self):
        data = {
            "points": self.points,
            "random": self.random_var.get(),
            "cycles": self.rep_var.get(),
            "infinite": self.infinite.get(),
            "start_hotkey": self.start_hotkey,
            "stop_hotkey": self.stop_hotkey,
            "start_enabled": self.g_hotkey_enabled.get(),
            "stop_enabled": self.s_hotkey_enabled.get(),
            "always_on_top": self.always_on_top.get()
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
        if self.is_running:
            messagebox.showwarning("Warning", "Stop first.")
            return
        path = filedialog.askopenfilename(filetypes=[("JSON Profile", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.points = data.get("points", [])
            self.refresh_points_list()
            self.random_var.set(data.get("random", 0))
            self.rep_var.set(data.get("cycles", 1))
            self.infinite.set(data.get("infinite", False))
            self.toggle_infinite()
            self.start_hotkey = data.get("start_hotkey", "g")
            self.stop_hotkey = data.get("stop_hotkey", "s")
            self.start_hk_label.config(text=f"Start: {self.start_hotkey.upper()}")
            self.stop_hk_label.config(text=f"Stop:  {self.stop_hotkey.upper()}")
            self.g_hotkey_enabled.set(data.get("start_enabled", True))
            self.s_hotkey_enabled.set(data.get("stop_enabled", True))
            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_topmost()
            self.selected_index = None
            self.disable_point_settings()
            self.status_label.config(text="Profile loaded", fg="#a6e3a1")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exit_app(self):
        self.stop_flag = True
        self.is_running = False
        if self.click_listener and self.click_listener.is_alive():
            self.click_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
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
        self.root.geometry("500x780")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.version = "v2.0"

        # State
        self.points = []                  # list of (x, y)
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

        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())

        self.setup_ui()
        self.start_keyboard_listener()
        self.update_mouse_pos()

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
        style.configure("TButton", padding=5, font=("Segoe UI", 9))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 9))
        style.configure("TCombobox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TSpinbox", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TLabelframe", background="#1e1e2e", foreground="#89b4fa")
        style.configure("TLabelframe.Label", background="#1e1e2e", foreground="#89b4fa", font=("Segoe UI", 10, "bold"))

        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        # Title
        tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 18, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 4))

        # Live mouse position
        self.mouse_pos_label = tk.Label(self.root, text="Mouse: (0, 0)", font=("Segoe UI", 10),
                                        bg="#1e1e2e", fg="#f9e2af")
        self.mouse_pos_label.pack(pady=(0, 6))

        # ========== Points Section ==========
        points_frame = ttk.LabelFrame(self.root, text=" Click Points (Sequence) ", padding=8)
        points_frame.pack(fill="x", padx=16, pady=4)

        list_frame = tk.Frame(points_frame, bg="#1e1e2e")
        list_frame.pack(fill="x")

        self.points_listbox = tk.Listbox(list_frame, height=5, bg="#313244", fg="#cdd6f4",
                                         selectbackground="#89b4fa", font=("Consolas", 10),
                                         relief="flat", highlightthickness=0)
        self.points_listbox.pack(side="left", fill="x", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.points_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.points_listbox.config(yscrollcommand=scrollbar.set)

        btn_row = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(6, 0))

        self.add_btn = ttk.Button(btn_row, text="Add Point", command=self.add_point)
        self.add_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.remove_btn = ttk.Button(btn_row, text="Remove", command=self.remove_point)
        self.remove_btn.pack(side="left", expand=True, fill="x", padx=4)

        self.clear_btn = ttk.Button(btn_row, text="Clear All", command=self.clear_points)
        self.clear_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ========== Click Settings ==========
        settings_frame = ttk.LabelFrame(self.root, text=" Click Settings ", padding=8)
        settings_frame.pack(fill="x", padx=16, pady=4)

        # Click Type
        type_row = tk.Frame(settings_frame, bg="#1e1e2e")
        type_row.pack(fill="x", pady=2)
        tk.Label(type_row, text="Click Type:", bg="#1e1e2e", fg="#cdd6f4", width=16, anchor="w").pack(side="left")
        self.click_type = tk.StringVar(value="Left")
        type_combo = ttk.Combobox(type_row, textvariable=self.click_type,
                                  values=["Left", "Right", "Double", "Middle"],
                                  state="readonly", width=12)
        type_combo.pack(side="left")

        # Hold
        hold_row = tk.Frame(settings_frame, bg="#1e1e2e")
        hold_row.pack(fill="x", pady=2)
        tk.Label(hold_row, text="Hold Duration (ms):", bg="#1e1e2e", fg="#cdd6f4", width=16, anchor="w").pack(side="left")
        self.hold_var = tk.IntVar(value=50)
        ttk.Spinbox(hold_row, from_=10, to=1000, textvariable=self.hold_var, width=10,
                    validate="key", validatecommand=vcmd).pack(side="left")

        # Interval
        interval_row = tk.Frame(settings_frame, bg="#1e1e2e")
        interval_row.pack(fill="x", pady=2)
        tk.Label(interval_row, text="Interval (ms):", bg="#1e1e2e", fg="#cdd6f4", width=16, anchor="w").pack(side="left")
        self.interval_var = tk.IntVar(value=100)
        ttk.Spinbox(interval_row, from_=1, to=10000, textvariable=self.interval_var, width=10,
                    validate="key", validatecommand=vcmd).pack(side="left")

        # Random
        random_row = tk.Frame(settings_frame, bg="#1e1e2e")
        random_row.pack(fill="x", pady=2)
        tk.Label(random_row, text="Random ± (ms):", bg="#1e1e2e", fg="#cdd6f4", width=16, anchor="w").pack(side="left")
        self.random_var = tk.IntVar(value=0)
        ttk.Spinbox(random_row, from_=0, to=500, textvariable=self.random_var, width=10,
                    validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(random_row, text="  (0 = off)", bg="#1e1e2e", fg="#6c7086").pack(side="left")

        # Repetitions
        rep_row = tk.Frame(settings_frame, bg="#1e1e2e")
        rep_row.pack(fill="x", pady=2)
        tk.Label(rep_row, text="Number of Clicks:", bg="#1e1e2e", fg="#cdd6f4", width=16, anchor="w").pack(side="left")
        self.rep_var = tk.IntVar(value=10)
        self.rep_spin = ttk.Spinbox(rep_row, from_=1, to=999999, textvariable=self.rep_var, width=10,
                                    validate="key", validatecommand=vcmd)
        self.rep_spin.pack(side="left")
        ttk.Checkbutton(rep_row, text="Infinite", variable=self.infinite,
                        command=self.toggle_infinite).pack(side="left", padx=8)

        # Always on Top
        top_row = tk.Frame(settings_frame, bg="#1e1e2e")
        top_row.pack(fill="x", pady=4)
        ttk.Checkbutton(top_row, text="Always on Top", variable=self.always_on_top,
                        command=self.toggle_topmost).pack(side="left")

        # ========== Hotkeys ==========
        hotkey_frame = ttk.LabelFrame(self.root, text=" Hotkeys ", padding=8)
        hotkey_frame.pack(fill="x", padx=16, pady=4)

        # Start
        start_hk = tk.Frame(hotkey_frame, bg="#1e1e2e")
        start_hk.pack(fill="x", pady=2)
        self.start_hk_label = tk.Label(start_hk, text=f"Start:  {self.start_hotkey.upper()}",
                                       bg="#1e1e2e", fg="#cdd6f4", width=14, anchor="w")
        self.start_hk_label.pack(side="left")
        ttk.Button(start_hk, text="Change", width=8,
                   command=lambda: self.change_hotkey("start")).pack(side="left", padx=4)
        ttk.Checkbutton(start_hk, text="Enable", variable=self.g_hotkey_enabled).pack(side="left")

        # Stop
        stop_hk = tk.Frame(hotkey_frame, bg="#1e1e2e")
        stop_hk.pack(fill="x", pady=2)
        self.stop_hk_label = tk.Label(stop_hk, text=f"Stop:   {self.stop_hotkey.upper()}",
                                      bg="#1e1e2e", fg="#cdd6f4", width=14, anchor="w")
        self.stop_hk_label.pack(side="left")
        ttk.Button(stop_hk, text="Change", width=8,
                   command=lambda: self.change_hotkey("stop")).pack(side="left", padx=4)
        ttk.Checkbutton(stop_hk, text="Enable", variable=self.s_hotkey_enabled).pack(side="left")

        # ========== Profile Buttons ==========
        profile_frame = tk.Frame(self.root, bg="#1e1e2e")
        profile_frame.pack(fill="x", padx=16, pady=6)

        ttk.Button(profile_frame, text="Save Profile", command=self.save_profile).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(profile_frame, text="Load Profile", command=self.load_profile).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ========== Action Buttons ==========
        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(fill="x", padx=16, pady=6)

        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=4)

        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Status + Version
        bottom = tk.Frame(self.root, bg="#1e1e2e")
        bottom.pack(side="bottom", fill="x", padx=16, pady=8)

        self.status_label = tk.Label(bottom, text="Ready", font=("Segoe UI", 10),
                                     bg="#1e1e2e", fg="#f9e2af")
        self.status_label.pack(side="left")

        tk.Label(bottom, text=self.version, font=("Segoe UI", 9),
                 bg="#1e1e2e", fg="#6c7086").pack(side="right")

    def update_mouse_pos(self):
        try:
            x, y = self.mouse.position
            self.mouse_pos_label.config(text=f"Mouse: ({x}, {y})")
        except Exception:
            pass
        self.root.after(60, self.update_mouse_pos)

    def toggle_infinite(self):
        self.rep_spin.config(state="disabled" if self.infinite.get() else "normal")

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    def refresh_points_list(self):
        self.points_listbox.delete(0, tk.END)
        for i, (x, y) in enumerate(self.points, 1):
            self.points_listbox.insert(tk.END, f"{i}.  ({x}, {y})")

    def add_point(self):
        if self.is_running:
            return
        self.status_label.config(text="Click anywhere to add a point...", fg="#f9e2af")
        self.add_btn.config(state="disabled")

        def on_click(x, y, button, pressed):
            if pressed and button == Button.left:
                self.points.append((x, y))
                self.refresh_points_list()
                self.status_label.config(text=f"Point added: ({x}, {y})", fg="#a6e3a1")
                self.add_btn.config(state="normal")
                return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def remove_point(self):
        if self.is_running:
            return
        sel = self.points_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.points[idx]
        self.refresh_points_list()
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_running:
            return
        self.points.clear()
        self.refresh_points_list()
        self.status_label.config(text="All points cleared", fg="#f9e2af")

    def change_hotkey(self, which):
        self.force_english_keyboard()
        self.waiting_for_hotkey = which
        self.status_label.config(text=f"Press an English key for {which.upper()} hotkey...", fg="#f9e2af")

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                if self.waiting_for_hotkey:
                    char = None
                    if hasattr(key, "char") and key.char:
                        char = key.char.lower()
                    elif key == Key.esc:
                        self.waiting_for_hotkey = None
                        self.status_label.config(text="Hotkey change cancelled", fg="#f9e2af")
                        return

                    if char and char.isascii() and char.isalpha():
                        if self.waiting_for_hotkey == "start":
                            if char == self.stop_hotkey:
                                self.status_label.config(text="Cannot use same key!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.start_hotkey = char
                            self.start_hk_label.config(text=f"Start:  {char.upper()}")
                        else:
                            if char == self.start_hotkey:
                                self.status_label.config(text="Cannot use same key!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.stop_hotkey = char
                            self.stop_hk_label.config(text=f"Stop:   {char.upper()}")

                        self.status_label.config(text=f"Hotkey set to {char.upper()}", fg="#a6e3a1")
                        self.waiting_for_hotkey = None
                    else:
                        self.status_label.config(text="Only English letters allowed!", fg="#f38ba8")
                    return

                if self.is_focus_on_input():
                    return

                if hasattr(key, "char") and key.char:
                    pressed = key.char.lower()
                    if (self.g_hotkey_enabled.get() and pressed == self.start_hotkey and not self.is_running):
                        self.root.after(0, self.start_clicking)
                    if (self.s_hotkey_enabled.get() and pressed == self.stop_hotkey and self.is_running):
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
            messagebox.showwarning("Warning", "Please add at least one point!")
            return
        if self.is_running:
            return

        hold_ms = self.get_safe_int(self.hold_var, 50, 10, 1000)
        interval_ms = self.get_safe_int(self.interval_var, 100, 1, 10000)
        random_ms = self.get_safe_int(self.random_var, 0, 0, 500)
        rep_count = self.get_safe_int(self.rep_var, 10, 1, 999999)

        self.hold_var.set(hold_ms)
        self.interval_var.set(interval_ms)
        self.random_var.set(random_ms)
        self.rep_var.set(rep_count)

        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.add_btn.config(state="disabled")
        self.remove_btn.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")

        thread = threading.Thread(
            target=self.click_loop,
            args=(hold_ms, interval_ms, random_ms, rep_count),
            daemon=True
        )
        thread.start()

    def perform_one_click(self, pos, hold_ms):
        self.mouse.position = pos
        click_type = self.click_type.get()

        if click_type == "Left":
            btn = Button.left
        elif click_type == "Right":
            btn = Button.right
        elif click_type == "Middle":
            btn = Button.middle
        else:  # Double
            btn = Button.left

        if click_type == "Double":
            self.mouse.click(btn, 2)
        else:
            self.mouse.press(btn)
            time.sleep(hold_ms / 1000.0)
            self.mouse.release(btn)

    def click_loop(self, hold_ms, interval_ms, random_ms, max_count):
        count = 0
        if self.infinite.get():
            max_count = float("inf")

        idx = 0
        total_points = len(self.points)

        while not self.stop_flag and count < max_count:
            pos = self.points[idx % total_points]
            self.perform_one_click(pos, hold_ms)

            count += 1
            idx += 1

            if self.stop_flag:
                break

            # Calculate delay with random
            delay = interval_ms
            if random_ms > 0:
                delay += random.randint(-random_ms, random_ms)
                delay = max(1, delay)

            time.sleep(delay / 1000.0)

        self.is_running = False
        self.root.after(0, self.on_clicking_finished)

    def on_clicking_finished(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.add_btn.config(state="normal")
        self.remove_btn.config(state="normal")
        self.clear_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")

    def stop_clicking(self):
        self.stop_flag = True
        self.status_label.config(text="Stopping...", fg="#f9e2af")

    def save_profile(self):
        data = {
            "points": self.points,
            "hold": self.hold_var.get(),
            "interval": self.interval_var.get(),
            "random": self.random_var.get(),
            "repetitions": self.rep_var.get(),
            "infinite": self.infinite.get(),
            "click_type": self.click_type.get(),
            "start_hotkey": self.start_hotkey,
            "stop_hotkey": self.stop_hotkey,
            "start_enabled": self.g_hotkey_enabled.get(),
            "stop_enabled": self.s_hotkey_enabled.get(),
            "always_on_top": self.always_on_top.get()
        }
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Profile", "*.json")],
            title="Save Profile"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                self.status_label.config(text="Profile saved successfully", fg="#a6e3a1")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save:\n{e}")

    def load_profile(self):
        if self.is_running:
            messagebox.showwarning("Warning", "Stop the clicker before loading a profile.")
            return
        path = filedialog.askopenfilename(
            filetypes=[("JSON Profile", "*.json")],
            title="Load Profile"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.points = [tuple(p) for p in data.get("points", [])]
            self.refresh_points_list()

            self.hold_var.set(data.get("hold", 50))
            self.interval_var.set(data.get("interval", 100))
            self.random_var.set(data.get("random", 0))
            self.rep_var.set(data.get("repetitions", 10))
            self.infinite.set(data.get("infinite", False))
            self.toggle_infinite()

            self.click_type.set(data.get("click_type", "Left"))
            self.start_hotkey = data.get("start_hotkey", "g")
            self.stop_hotkey = data.get("stop_hotkey", "s")
            self.start_hk_label.config(text=f"Start:  {self.start_hotkey.upper()}")
            self.stop_hk_label.config(text=f"Stop:   {self.stop_hotkey.upper()}")

            self.g_hotkey_enabled.set(data.get("start_enabled", True))
            self.s_hotkey_enabled.set(data.get("stop_enabled", True))
            self.always_on_top.set(data.get("always_on_top", False))
            self.toggle_topmost()

            self.status_label.config(text="Profile loaded successfully", fg="#a6e3a1")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load:\n{e}")

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
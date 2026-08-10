import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import ctypes
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Listener as KeyboardListener

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.geometry("440x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        # Version
        self.version = "v1.4"

        # State
        self.coords = None
        self.is_running = False
        self.stop_flag = False
        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)

        # Hotkeys (always English lowercase)
        self.start_hotkey = "g"
        self.stop_hotkey = "s"

        self.mouse = MouseController()
        self.click_listener = None
        self.keyboard_listener = None
        self.waiting_for_hotkey = None  # "start" or "stop"

        # Force English keyboard layout
        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())

        self.setup_ui()
        self.start_keyboard_listener()

    def force_english_keyboard(self):
        """Force the keyboard layout to English (US)"""
        try:
            ctypes.windll.user32.LoadKeyboardLayoutW("00000409", 1)
        except Exception:
            pass

    def is_focus_on_input(self):
        """Check if current focus is on an Entry or Spinbox"""
        focused = self.root.focus_get()
        if focused is None:
            return False
        widget_class = focused.winfo_class()
        return widget_class in ("TEntry", "TSpinbox", "Entry", "Spinbox")

    def validate_number(self, action, value_if_allowed):
        """Only allow digits (and empty string) in number fields"""
        if action == "1":  # 1 = insertion
            return value_if_allowed.isdigit() or value_if_allowed == ""
        return True

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TSpinbox", fieldbackground="#313244", foreground="#cdd6f4")

        # Validation command for number-only fields
        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        # Title
        title = tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 18, "bold"),
                         bg="#1e1e2e", fg="#89b4fa")
        title.pack(pady=(12, 8))

        # Coordinates section
        coord_frame = tk.Frame(self.root, bg="#1e1e2e")
        coord_frame.pack(pady=4, fill="x", padx=20)

        self.coord_label = tk.Label(coord_frame, text="Coordinates: Not set",
                                    font=("Segoe UI", 11), bg="#1e1e2e", fg="#a6e3a1")
        self.coord_label.pack(anchor="w")

        btn_frame = tk.Frame(coord_frame, bg="#1e1e2e")
        btn_frame.pack(fill="x", pady=4)

        self.set_btn = ttk.Button(btn_frame, text="Set Coordinates", command=self.set_coordinates)
        self.set_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.correct_btn = ttk.Button(btn_frame, text="Correct Coordinates", command=self.correct_coordinates)
        self.correct_btn.pack(side="left", expand=True, fill="x")

        # Hold time
        hold_frame = tk.Frame(self.root, bg="#1e1e2e")
        hold_frame.pack(pady=6, fill="x", padx=20)

        tk.Label(hold_frame, text="Hold Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.hold_var = tk.IntVar(value=50)
        ttk.Spinbox(hold_frame, from_=10, to=1000, textvariable=self.hold_var, width=12,
                    validate="key", validatecommand=vcmd).pack(anchor="w", pady=2)

        # Interval
        interval_frame = tk.Frame(self.root, bg="#1e1e2e")
        interval_frame.pack(pady=6, fill="x", padx=20)

        tk.Label(interval_frame, text="Interval Between Clicks (ms):", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.interval_var = tk.IntVar(value=100)
        ttk.Spinbox(interval_frame, from_=1, to=10000, textvariable=self.interval_var, width=12,
                    validate="key", validatecommand=vcmd).pack(anchor="w", pady=2)

        # Repetitions
        rep_frame = tk.Frame(self.root, bg="#1e1e2e")
        rep_frame.pack(pady=6, fill="x", padx=20)

        tk.Label(rep_frame, text="Number of Clicks:", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        rep_inner = tk.Frame(rep_frame, bg="#1e1e2e")
        rep_inner.pack(anchor="w", pady=2)

        self.rep_var = tk.IntVar(value=10)
        self.rep_spin = ttk.Spinbox(rep_inner, from_=1, to=999999, textvariable=self.rep_var, width=12,
                                    validate="key", validatecommand=vcmd)
        self.rep_spin.pack(side="left")

        ttk.Checkbutton(rep_inner, text="Infinite", variable=self.infinite,
                        command=self.toggle_infinite).pack(side="left", padx=10)

        # === Hotkeys Section ===
        hotkey_frame = tk.LabelFrame(self.root, text=" Hotkeys ", bg="#1e1e2e", fg="#89b4fa",
                                     font=("Segoe UI", 10, "bold"), padx=10, pady=6)
        hotkey_frame.pack(pady=8, fill="x", padx=20)

        # Start hotkey
        start_hk_frame = tk.Frame(hotkey_frame, bg="#1e1e2e")
        start_hk_frame.pack(fill="x", pady=3)

        self.start_hk_label = tk.Label(start_hk_frame, text=f"Start Hotkey:  {self.start_hotkey.upper()}",
                                       bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w")
        self.start_hk_label.pack(side="left")

        ttk.Button(start_hk_frame, text="Change", width=8,
                   command=lambda: self.change_hotkey("start")).pack(side="left", padx=5)

        ttk.Checkbutton(start_hk_frame, text="Enable", variable=self.g_hotkey_enabled).pack(side="left", padx=5)

        # Stop hotkey
        stop_hk_frame = tk.Frame(hotkey_frame, bg="#1e1e2e")
        stop_hk_frame.pack(fill="x", pady=3)

        self.stop_hk_label = tk.Label(stop_hk_frame, text=f"Stop Hotkey:   {self.stop_hotkey.upper()}",
                                      bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w")
        self.stop_hk_label.pack(side="left")

        ttk.Button(stop_hk_frame, text="Change", width=8,
                   command=lambda: self.change_hotkey("stop")).pack(side="left", padx=5)

        ttk.Checkbutton(stop_hk_frame, text="Enable", variable=self.s_hotkey_enabled).pack(side="left", padx=5)

        # Action buttons
        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(pady=10, fill="x", padx=20)

        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.stop_btn = ttk.Button(action_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x")

        # Status + Version
        bottom_frame = tk.Frame(self.root, bg="#1e1e2e")
        bottom_frame.pack(side="bottom", fill="x", padx=15, pady=8)

        self.status_label = tk.Label(bottom_frame, text="Ready", font=("Segoe UI", 10),
                                     bg="#1e1e2e", fg="#f9e2af")
        self.status_label.pack(side="left")

        version_label = tk.Label(bottom_frame, text=self.version, font=("Segoe UI", 9),
                                 bg="#1e1e2e", fg="#6c7086")
        version_label.pack(side="right")

    def toggle_infinite(self):
        self.rep_spin.config(state="disabled" if self.infinite.get() else "normal")

    def set_coordinates(self):
        self.status_label.config(text="Click anywhere to set coordinates...", fg="#f9e2af")
        self.set_btn.config(state="disabled")
        self.correct_btn.config(state="disabled")

        def on_click(x, y, button, pressed):
            if pressed and button == Button.left:
                self.coords = (x, y)
                self.coord_label.config(text=f"Coordinates: ({x}, {y})")
                self.status_label.config(text="Coordinates set successfully!", fg="#a6e3a1")
                self.set_btn.config(state="normal")
                self.correct_btn.config(state="normal")
                return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def correct_coordinates(self):
        self.coords = None
        self.coord_label.config(text="Coordinates: Not set")
        self.status_label.config(text="Previous coordinates cleared. Click to set new ones...", fg="#f9e2af")
        self.set_coordinates()

    def change_hotkey(self, which):
        """Wait for the next key press to set a new hotkey (English only)"""
        self.force_english_keyboard()
        self.waiting_for_hotkey = which
        self.status_label.config(text=f"Press an English key to set new {which.upper()} hotkey...", fg="#f9e2af")

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                # If changing hotkey → always process
                if self.waiting_for_hotkey:
                    char = None
                    if hasattr(key, "char") and key.char:
                        char = key.char.lower()
                    elif key == Key.space:
                        char = "space"
                    elif key == Key.esc:
                        self.waiting_for_hotkey = None
                        self.status_label.config(text="Hotkey change cancelled", fg="#f9e2af")
                        return

                    if char and char.isascii() and char.isalpha():
                        if self.waiting_for_hotkey == "start":
                            if char == self.stop_hotkey:
                                self.status_label.config(text="Cannot use the same key for Start and Stop!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.start_hotkey = char
                            self.start_hk_label.config(text=f"Start Hotkey:  {char.upper()}")
                        elif self.waiting_for_hotkey == "stop":
                            if char == self.start_hotkey:
                                self.status_label.config(text="Cannot use the same key for Start and Stop!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.stop_hotkey = char
                            self.stop_hk_label.config(text=f"Stop Hotkey:   {char.upper()}")

                        self.status_label.config(
                            text=f"{self.waiting_for_hotkey.capitalize()} hotkey set to: {char.upper()}",
                            fg="#a6e3a1"
                        )
                        self.waiting_for_hotkey = None
                    else:
                        self.status_label.config(text="Only English letters are allowed!", fg="#f38ba8")
                    return

                # Ignore hotkeys while typing in number fields
                if self.is_focus_on_input():
                    return

                # Normal hotkey handling
                if hasattr(key, "char") and key.char:
                    pressed = key.char.lower()

                    # Start hotkey
                    if (self.g_hotkey_enabled.get() and
                            pressed == self.start_hotkey and
                            not self.is_running):
                        self.root.after(0, self.start_clicking)

                    # Stop hotkey
                    if (self.s_hotkey_enabled.get() and
                            pressed == self.stop_hotkey and
                            self.is_running):
                        self.root.after(0, self.stop_clicking)

            except AttributeError:
                pass

        self.keyboard_listener = KeyboardListener(on_press=on_press)
        self.keyboard_listener.start()

    def get_safe_int(self, var, default, min_val=1, max_val=999999):
        """Safely get integer value from IntVar / Spinbox"""
        try:
            value = int(var.get())
            if value < min_val:
                value = min_val
            if value > max_val:
                value = max_val
            return value
        except (tk.TclError, ValueError, TypeError):
            return default

    def start_clicking(self):
        if self.coords is None:
            messagebox.showwarning("Warning", "Please set coordinates first!")
            return

        if self.is_running:
            return

        # Validate numbers before starting
        hold_ms = self.get_safe_int(self.hold_var, 50, 10, 1000)
        interval_ms = self.get_safe_int(self.interval_var, 100, 1, 10000)
        rep_count = self.get_safe_int(self.rep_var, 10, 1, 999999)

        # Update the variables with cleaned values
        self.hold_var.set(hold_ms)
        self.interval_var.set(interval_ms)
        self.rep_var.set(rep_count)

        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.set_btn.config(state="disabled")
        self.correct_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")

        thread = threading.Thread(target=self.click_loop, args=(hold_ms, interval_ms, rep_count), daemon=True)
        thread.start()

    def click_loop(self, hold_ms, interval_ms, max_count):
        count = 0
        if self.infinite.get():
            max_count = float("inf")

        while not self.stop_flag and count < max_count:
            self.mouse.position = self.coords
            self.mouse.press(Button.left)
            time.sleep(hold_ms / 1000.0)
            self.mouse.release(Button.left)

            count += 1
            if self.stop_flag:
                break
            time.sleep(interval_ms / 1000.0)

        self.is_running = False
        self.root.after(0, self.on_clicking_finished)

    def on_clicking_finished(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.set_btn.config(state="normal")
        self.correct_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")

    def stop_clicking(self):
        self.stop_flag = True
        self.status_label.config(text="Stopping...", fg="#f9e2af")

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
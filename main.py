import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Listener as KeyboardListener

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker")
        self.root.geometry("420x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        # State
        self.coords = None
        self.is_running = False
        self.stop_flag = False
        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.mouse = MouseController()
        self.click_listener = None
        self.keyboard_listener = None

        self.setup_ui()
        self.start_keyboard_listener()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="#313244", foreground="#cdd6f4")
        style.configure("TSpinbox", fieldbackground="#313244", foreground="#cdd6f4")

        # Title
        title = tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 18, "bold"),
                         bg="#1e1e2e", fg="#89b4fa")
        title.pack(pady=(15, 10))

        # Coordinates section
        coord_frame = tk.Frame(self.root, bg="#1e1e2e")
        coord_frame.pack(pady=5, fill="x", padx=20)

        self.coord_label = tk.Label(coord_frame, text="Coordinates: Not set",
                                    font=("Segoe UI", 11), bg="#1e1e2e", fg="#a6e3a1")
        self.coord_label.pack(anchor="w")

        btn_frame = tk.Frame(coord_frame, bg="#1e1e2e")
        btn_frame.pack(fill="x", pady=5)

        self.set_btn = ttk.Button(btn_frame, text="Set Coordinates", command=self.set_coordinates)
        self.set_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.correct_btn = ttk.Button(btn_frame, text="Correct Coordinates", command=self.correct_coordinates)
        self.correct_btn.pack(side="left", expand=True, fill="x")

        # Hold time
        hold_frame = tk.Frame(self.root, bg="#1e1e2e")
        hold_frame.pack(pady=8, fill="x", padx=20)

        tk.Label(hold_frame, text="Hold Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.hold_var = tk.IntVar(value=50)
        hold_spin = ttk.Spinbox(hold_frame, from_=10, to=1000, textvariable=self.hold_var, width=12)
        hold_spin.pack(anchor="w", pady=2)

        # Interval
        interval_frame = tk.Frame(self.root, bg="#1e1e2e")
        interval_frame.pack(pady=8, fill="x", padx=20)

        tk.Label(interval_frame, text="Interval Between Clicks (ms):", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        self.interval_var = tk.IntVar(value=100)
        interval_spin = ttk.Spinbox(interval_frame, from_=1, to=10000, textvariable=self.interval_var, width=12)
        interval_spin.pack(anchor="w", pady=2)

        # Repetitions
        rep_frame = tk.Frame(self.root, bg="#1e1e2e")
        rep_frame.pack(pady=8, fill="x", padx=20)

        tk.Label(rep_frame, text="Number of Clicks:", bg="#1e1e2e", fg="#cdd6f4").pack(anchor="w")
        rep_inner = tk.Frame(rep_frame, bg="#1e1e2e")
        rep_inner.pack(anchor="w", pady=2)

        self.rep_var = tk.IntVar(value=10)
        self.rep_spin = ttk.Spinbox(rep_inner, from_=1, to=999999, textvariable=self.rep_var, width=12)
        self.rep_spin.pack(side="left")

        self.infinite_check = ttk.Checkbutton(rep_inner, text="Infinite", variable=self.infinite,
                                              command=self.toggle_infinite)
        self.infinite_check.pack(side="left", padx=10)

        # Stop section
        stop_frame = tk.Frame(self.root, bg="#1e1e2e")
        stop_frame.pack(pady=10, fill="x", padx=20)

        self.stop_btn = ttk.Button(stop_frame, text="Stop", command=self.stop_clicking, state="disabled")
        self.stop_btn.pack(side="left")

        self.s_check = ttk.Checkbutton(stop_frame, text="Enable 'S' hotkey to Stop",
                                       variable=self.s_hotkey_enabled)
        self.s_check.pack(side="left", padx=15)

        # Start / Exit
        action_frame = tk.Frame(self.root, bg="#1e1e2e")
        action_frame.pack(pady=15, fill="x", padx=20)

        self.start_btn = ttk.Button(action_frame, text="Start", command=self.start_clicking)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.exit_btn = ttk.Button(action_frame, text="Exit", command=self.exit_app)
        self.exit_btn.pack(side="left", expand=True, fill="x")

        # Status
        self.status_label = tk.Label(self.root, text="Ready", font=("Segoe UI", 10),
                                     bg="#1e1e2e", fg="#f9e2af")
        self.status_label.pack(pady=10)

    def toggle_infinite(self):
        if self.infinite.get():
            self.rep_spin.config(state="disabled")
        else:
            self.rep_spin.config(state="normal")

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
                return False  # Stop listener

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def correct_coordinates(self):
        self.coords = None
        self.coord_label.config(text="Coordinates: Not set")
        self.status_label.config(text="Previous coordinates cleared. Click to set new ones...", fg="#f9e2af")
        self.set_coordinates()

    def start_keyboard_listener(self):
        def on_press(key):
            try:
                if self.s_hotkey_enabled.get() and self.is_running:
                    if key.char and key.char.lower() == 's':
                        self.stop_clicking()
            except AttributeError:
                pass

        self.keyboard_listener = KeyboardListener(on_press=on_press)
        self.keyboard_listener.start()

    def start_clicking(self):
        if self.coords is None:
            messagebox.showwarning("Warning", "Please set coordinates first!")
            return

        if self.is_running:
            return

        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.set_btn.config(state="disabled")
        self.correct_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")

        thread = threading.Thread(target=self.click_loop, daemon=True)
        thread.start()

    def click_loop(self):
        hold_ms = self.hold_var.get()
        interval_ms = self.interval_var.get()
        count = 0
        max_count = self.rep_var.get() if not self.infinite.get() else float('inf')

        while not self.stop_flag and count < max_count:
            # Move and press
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
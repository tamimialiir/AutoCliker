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
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)

        self.version = "v2.8"

        self.points = []
        self.selected_index = None
        self.is_running = False
        self.stop_flag = False
        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)

        self.start_hotkey = "s"
        self.stop_hotkey = "e"

        self.mouse = MouseController()
        self.click_listener = None
        self.keyboard_listener = None
        self.waiting_for_hotkey = None
        self.adding_mode = None
        self.temp_drag_start = None

        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())

        self.setup_ui()
        self.start_keyboard_listener()

        self.root.update_idletasks()
        self.root.geometry(f"500x{self.root.winfo_reqheight()}")

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

        vcmd = (self.root.register(self.validate_number), "%d", "%P")

        tk.Label(self.root, text="Auto Clicker", font=("Segoe UI", 15, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(6, 3))

        # Defaults
        settings_frame = ttk.LabelFrame(self.root, text=" Defaults for New Points ", padding=5)
        settings_frame.pack(fill="x", padx=10, pady=2)

        row1 = tk.Frame(settings_frame, bg="#1e1e2e")
        row1.pack(fill="x", pady=1)

        tk.Label(row1, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4", width=11, anchor="w").pack(side="left")
        self.pt_hold_var = tk.IntVar(value=50)
        ttk.Spinbox(row1, from_=10, to=2000, textvariable=self.pt_hold_var, width=7,
                    validate="key", validatecommand=vcmd).pack(side="left")

        tk.Label(row1, text="  Clicks:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(6, 0))
        self.pt_count_var = tk.IntVar(value=1)
        ttk.Spinbox(row1, from_=1, to=100, textvariable=self.pt_count_var, width=5,
                    validate="key", validatecommand=vcmd).pack(side="left")

        tk.Label(row1, text="  Type:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(6, 0))
        self.pt_type_var = tk.StringVar(value="Left")
        self.pt_type_combo = ttk.Combobox(row1, textvariable=self.pt_type_var,
                                          values=["Left", "Right", "Double", "Middle"],
                                          state="readonly", width=8)
        self.pt_type_combo.pack(side="left")
        self.pt_type_combo.set("Left")

        row2 = tk.Frame(settings_frame, bg="#1e1e2e")
        row2.pack(fill="x", pady=1)

        tk.Label(row2, text="Delay After (ms):", bg="#1e1e2e", fg="#cdd6f4", width=11, anchor="w").pack(side="left")
        self.pt_delay_var = tk.IntVar(value=100)
        ttk.Spinbox(row2, from_=0, to=10000, textvariable=self.pt_delay_var, width=7,
                    validate="key", validatecommand=vcmd).pack(side="left")

        # Points List
        points_frame = ttk.LabelFrame(self.root, text=" Points Sequence ", padding=5)
        points_frame.pack(fill="x", padx=10, pady=2)

        list_frame = tk.Frame(points_frame, bg="#1e1e2e")
        list_frame.pack(fill="x")

        self.points_listbox = tk.Listbox(list_frame, height=6, bg="#313244", fg="#cdd6f4",
                                         selectbackground="#89b4fa", font=("Consolas", 9),
                                         relief="flat", highlightthickness=0)
        self.points_listbox.pack(side="left", fill="x", expand=True)
        self.points_listbox.bind("<<ListboxSelect>>", self.on_point_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.points_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.points_listbox.config(yscrollcommand=scrollbar.set)

        btn_row = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row.pack(fill="x", pady=(4, 0))

        ttk.Button(btn_row, text="Add Click", command=lambda: self.start_add_point("click")).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(btn_row, text="Add Drag", command=lambda: self.start_add_point("drag")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row, text="Add Wait", command=self.add_wait).pack(side="left", expand=True, fill="x", padx=2)

        btn_row2 = tk.Frame(points_frame, bg="#1e1e2e")
        btn_row2.pack(fill="x", pady=(3, 0))

        self.edit_btn = ttk.Button(btn_row2, text="Edit", command=self.open_edit_popup, state="disabled")
        self.edit_btn.pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(btn_row2, text="↑", width=3, command=self.move_up).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="↓", width=3, command=self.move_down).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Remove", command=self.remove_point).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(btn_row2, text="Clear", command=self.clear_points).pack(side="left", expand=True, fill="x", padx=(2, 0))

        # Global Settings
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

        # Hotkeys
        hotkey_frame = ttk.LabelFrame(self.root, text=" Hotkeys ", padding=5)
        hotkey_frame.pack(fill="x", padx=10, pady=2)

        hk1 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk1.pack(fill="x", pady=1)
        self.start_hk_label = tk.Label(hk1, text=f"Start Hotkey:  {self.start_hotkey.upper()}",
                                       bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w")
        self.start_hk_label.pack(side="left")
        ttk.Button(hk1, text="Change", width=7, command=lambda: self.change_hotkey("start")).pack(side="left", padx=4)
        ttk.Checkbutton(hk1, text="Enable", variable=self.g_hotkey_enabled).pack(side="left")

        hk2 = tk.Frame(hotkey_frame, bg="#1e1e2e")
        hk2.pack(fill="x", pady=1)
        self.stop_hk_label = tk.Label(hk2, text=f"Stop Hotkey:   {self.stop_hotkey.upper()}",
                                      bg="#1e1e2e", fg="#cdd6f4", width=18, anchor="w")
        self.stop_hk_label.pack(side="left")
        ttk.Button(hk2, text="Change", width=7, command=lambda: self.change_hotkey("stop")).pack(side="left", padx=4)
        ttk.Checkbutton(hk2, text="Enable", variable=self.s_hotkey_enabled).pack(side="left")

        # Profile + Actions
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
        tk.Label(bottom, text=self.version, font=("Segoe UI", 8),
                 bg="#1e1e2e", fg="#6c7086").pack(side="right")

    def get_current_defaults(self):
        return {
            "hold": self.get_safe_int(self.pt_hold_var, 50, 10, 2000),
            "count": self.get_safe_int(self.pt_count_var, 1, 1, 100),
            "delay_after": self.get_safe_int(self.pt_delay_var, 100, 0, 10000),
            "type": self.pt_type_var.get()
        }

    def on_point_select(self, event=None):
        if self.is_running:
            return  # ignore manual selection while running
        sel = self.points_listbox.curselection()
        if sel:
            self.selected_index = sel[0]
            self.edit_btn.config(state="normal")
        else:
            if self.selected_index is None:
                self.edit_btn.config(state="disabled")

    def highlight_current(self, index):
        """Highlight the currently executing step in the list"""
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
            action = p.get("action")
            if action == "drag":
                text = f"{i}. DRAG ({p['x']},{p['y']}) → ({p['drag_x']},{p['drag_y']}) {p.get('hold', 300)}ms"
            elif action == "wait":
                text = f"{i}. WAIT {p.get('delay', 500)}ms"
            else:
                text = f"{i}. CLICK ({p['x']},{p['y']}) {p.get('type', 'Left')} x{p.get('count', 1)}"
            self.points_listbox.insert(tk.END, text)

    def open_edit_popup(self):
        if self.is_running or self.selected_index is None or self.selected_index >= len(self.points):
            return

        p = self.points[self.selected_index]
        action = p.get("action", "click")

        popup = tk.Toplevel(self.root)
        popup.title("Edit Item")
        popup.configure(bg="#1e1e2e")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        vcmd = (popup.register(self.validate_number), "%d", "%P")

        tk.Label(popup, text=f"Editing item #{self.selected_index + 1}", font=("Segoe UI", 11, "bold"),
                 bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 8))

        frame = tk.Frame(popup, bg="#1e1e2e")
        frame.pack(padx=15, pady=5)

        entries = {}

        if action == "wait":
            tk.Label(frame, text="Wait Duration (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=3)
            var = tk.IntVar(value=p.get("delay", 500))
            ttk.Spinbox(frame, from_=1, to=60000, textvariable=var, width=10,
                        validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=3, padx=5)
            entries["delay"] = var

        elif action == "drag":
            labels = [
                ("Start X:", "x"), ("Start Y:", "y"),
                ("End X:", "drag_x"), ("End Y:", "drag_y"),
                ("Duration (ms):", "hold"),
                ("Delay After (ms):", "delay_after")
            ]
            for i, (label, key) in enumerate(labels):
                tk.Label(frame, text=label, bg="#1e1e2e", fg="#cdd6f4").grid(row=i, column=0, sticky="w", pady=2)
                var = tk.IntVar(value=p.get(key, 0))
                ttk.Spinbox(frame, from_=0, to=99999 if key in ("hold", "delay_after") else 10000,
                            textvariable=var, width=10, validate="key", validatecommand=vcmd).grid(row=i, column=1, pady=2, padx=5)
                entries[key] = var

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

            tk.Label(frame, text="Hold (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=2, column=0, sticky="w", pady=2)
            var_hold = tk.IntVar(value=p.get("hold", 50))
            ttk.Spinbox(frame, from_=10, to=2000, textvariable=var_hold, width=10,
                        validate="key", validatecommand=vcmd).grid(row=2, column=1, pady=2, padx=5)
            entries["hold"] = var_hold

            tk.Label(frame, text="Clicks:", bg="#1e1e2e", fg="#cdd6f4").grid(row=3, column=0, sticky="w", pady=2)
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

            tk.Label(frame, text="Delay After (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=5, column=0, sticky="w", pady=2)
            var_delay = tk.IntVar(value=p.get("delay_after", 100))
            ttk.Spinbox(frame, from_=0, to=10000, textvariable=var_delay, width=10,
                        validate="key", validatecommand=vcmd).grid(row=5, column=1, pady=2, padx=5)
            entries["delay_after"] = var_delay

        def apply_changes():
            try:
                if action == "wait":
                    p["delay"] = max(1, int(entries["delay"].get()))
                elif action == "drag":
                    for key in ["x", "y", "drag_x", "drag_y", "hold", "delay_after"]:
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
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value:\n{e}", parent=popup)

        btn_frame = tk.Frame(popup, bg="#1e1e2e")
        btn_frame.pack(pady=12)

        ttk.Button(btn_frame, text="Apply", command=apply_changes, width=10).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancel", command=popup.destroy, width=10).pack(side="left", padx=6)

        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
        y = self.root.winfo_y() + 80
        popup.geometry(f"+{x}+{y}")

    def add_wait(self):
        if self.is_running:
            return
        delay = self.get_safe_int(self.pt_delay_var, 500, 1, 60000)
        point = {"action": "wait", "delay": delay}
        self.points.append(point)
        self.refresh_points_list()
        self.status_label.config(text=f"Wait {delay}ms added", fg="#a6e3a1")

    def minimize_for_capture(self):
        self.root.iconify()

    def restore_after_capture(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.after(150, lambda: self.root.attributes("-topmost", self.always_on_top.get()))

    def start_add_point(self, mode):
        if self.is_running:
            return

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
                    point = {"action": "click", "x": x, "y": y, **defaults}
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
                        "count": 1,
                        "delay_after": defaults["delay_after"],
                        "type": "Left"
                    }
                    self.points.append(point)
                    self.root.after(0, self.finish_add_point, "Drag point added")
                    return False

        self.click_listener = mouse.Listener(on_click=on_click)
        self.click_listener.start()

    def finish_add_point(self, message):
        self.adding_mode = None
        self.temp_drag_start = None
        self.refresh_points_list()
        self.restore_after_capture()
        self.status_label.config(text=message, fg="#a6e3a1")

    def move_up(self):
        if self.selected_index is None or self.selected_index == 0 or self.is_running:
            return
        i = self.selected_index
        self.points[i], self.points[i-1] = self.points[i-1], self.points[i]
        self.selected_index = i - 1
        self.refresh_points_list()
        self.points_listbox.selection_set(self.selected_index)
        self.edit_btn.config(state="normal")

    def move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.points)-1 or self.is_running:
            return
        i = self.selected_index
        self.points[i], self.points[i+1] = self.points[i+1], self.points[i]
        self.selected_index = i + 1
        self.refresh_points_list()
        self.points_listbox.selection_set(self.selected_index)
        self.edit_btn.config(state="normal")

    def remove_point(self):
        if self.is_running or self.selected_index is None:
            return
        del self.points[self.selected_index]
        self.selected_index = None
        self.edit_btn.config(state="disabled")
        self.refresh_points_list()
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_running:
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
                            self.start_hk_label.config(text=f"Start Hotkey:  {char.upper()}")
                        else:
                            if char == self.start_hotkey:
                                self.status_label.config(text="Same key not allowed!", fg="#f38ba8")
                                self.waiting_for_hotkey = None
                                return
                            self.stop_hotkey = char
                            self.stop_hk_label.config(text=f"Stop Hotkey:   {char.upper()}")
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
        self.edit_btn.config(state="disabled")
        self.status_label.config(text="Running...", fg="#89b4fa")

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

    def click_loop(self, random_ms, pos_rand, max_cycles):
        cycle = 0
        if self.infinite.get():
            max_cycles = float("inf")

        while not self.stop_flag and cycle < max_cycles:
            for idx, p in enumerate(self.points):
                if self.stop_flag:
                    break

                # Live highlight the current step
                self.root.after(0, self.highlight_current, idx)

                action = p.get("action")

                if action == "wait":
                    delay = p.get("delay", 500)
                    if random_ms > 0:
                        delay += random.randint(-random_ms, random_ms)
                    delay = max(0, delay)
                    time.sleep(delay / 1000.0)
                    continue

                if action == "drag":
                    self.perform_drag(p, pos_rand)
                else:
                    count = p.get("count", 1)
                    for _ in range(count):
                        if self.stop_flag:
                            break
                        self.perform_click(p, pos_rand)
                        if count > 1:
                            time.sleep(0.04)

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
        self.clear_highlight()
        if self.selected_index is not None:
            self.edit_btn.config(state="normal")
        self.status_label.config(text="Stopped", fg="#f38ba8")

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
            self.pos_random_var.set(data.get("pos_random", 0))
            self.rep_var.set(data.get("cycles", 1))
            self.infinite.set(data.get("infinite", False))
            self.toggle_infinite()
            self.start_hotkey = data.get("start_hotkey", "s")
            self.stop_hotkey = data.get("stop_hotkey", "e")
            self.start_hk_label.config(text=f"Start Hotkey:  {self.start_hotkey.upper()}")
            self.stop_hk_label.config(text=f"Stop Hotkey:   {self.stop_hotkey.upper()}")
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

            self.selected_index = None
            self.edit_btn.config(state="disabled")
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
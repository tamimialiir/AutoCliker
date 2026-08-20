import tkinter as tk
from tkinter import ttk, messagebox
import copy
from pynput import mouse
from pynput.mouse import Button
from pynput.keyboard import Listener as KeyboardListener
from utils import key_to_str, ACTION_COLORS

def open_add_popup(self, action, data):
    """Popup for configuring a newly captured Click or Drag before adding it to the list."""
    self.clear_previews()
    preview_main = None
    preview_end = None
    if action == "click":
        preview_main = self.show_point_preview(data.get("x", 0), data.get("y", 0), "#10b981", "C")
    elif action == "drag":
        preview_main = self.show_point_preview(data.get("x", 0), data.get("y", 0), "#10b981", "S")
        preview_end = self.show_point_preview(data.get("drag_x", 0), data.get("drag_y", 0), "#ef4444", "E")

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
            var = tk.IntVar(value=data.get(key, 1 if key == "count" else (300 if key == "hold" else 0)))
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
    """Popup for editing an existing item from the action list."""
    if self.selected_index is None or self.selected_index >= len(self.points) or self.is_busy():
        return
    p = self.points[self.selected_index]
    action = p.get("action")
    
    if action == "key":
        self._open_edit_key_popup(p)
        return
        
    self.clear_previews()
    preview_main = None
    preview_end = None
    
    if action == "click":
        preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#10b981", "C")
    elif action == "drag":
        preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#10b981", "S")
        preview_end = self.show_point_preview(p.get("drag_x", 0), p.get("drag_y", 0), "#ef4444", "E")
    elif action == "scroll":
        preview_main = self.show_point_preview(p.get("x", 0), p.get("y", 0), "#cba6f7", "Sc")
        
    popup = tk.Toplevel(self.root)
    popup.title("Edit Item")
    popup.configure(bg="#1e1e2e")
    popup.resizable(False, False)
    popup.transient(self.root)
    
    if action == "wait":
        popup.grab_set()
        
    def on_popup_close():
        self.clear_previews()
        popup.destroy()
        
    popup.protocol("WM_DELETE_WINDOW", on_popup_close)
    vcmd = (popup.register(self.validate_number), "%d", "%P")
    
    tk.Label(popup, text=f"Editing item #{self.selected_index + 1}", font=("Segoe UI", 11, "bold"),
             bg="#1e1e2e", fg="#89b4fa").pack(pady=(10, 6))
             
    if action != "wait":
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
        # click
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
    """Popup for adding a Wait (delay) action."""
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


def add_scroll_action(self, preset=None):
    """Popup for adding a Mouse Scroll action."""
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


def _open_edit_key_popup(self, p):
    """Edit a Key action — layout identical to Add Keyboard Action."""
    popup = tk.Toplevel(self.root)
    popup.title("Edit Item")
    popup.configure(bg="#1e1e2e")
    popup.resizable(False, False)
    popup.transient(self.root)
    popup.grab_set()
    
    vcmd = (popup.register(self.validate_number), "%d", "%P")
    tk.Label(popup, text=f"Editing item #{self.selected_index + 1}", font=("Segoe UI", 11, "bold"),
             bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 4))
    tk.Label(popup, text="Type manually or use Capture Key (Ctrl/Alt/Shift/Cmd + key)",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()
             
    name_frame = tk.Frame(popup, bg="#1e1e2e")
    name_frame.pack(fill="x", padx=20, pady=(10, 0))
    tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
    name_var = tk.StringVar(value=p.get("name", ""))
    ttk.Entry(name_frame, textvariable=name_var, width=18).pack(side="left", padx=(6, 0))
    
    key_row = tk.Frame(popup, bg="#1e1e2e")
    key_row.pack(fill="x", padx=20, pady=(10, 0))
    tk.Label(key_row, text="Key / Combo:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
    key_var = tk.StringVar(value=p.get("key", "a"))
    entry = ttk.Entry(key_row, textvariable=key_var, width=16, font=("Segoe UI", 10))
    entry.pack(side="left", padx=(6, 6))
    entry.focus_set()
    
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
        
    ttk.Button(key_row, text="Capture Key", command=capture_from_listener, width=12).pack(side="left")
    
    tk.Label(popup, text="Examples:  a  |  ctrl+c  |  shift+3  |  alt+F4  |  cmd+v",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack(pady=(4, 0))
             
    opts = tk.Frame(popup, bg="#1e1e2e")
    opts.pack(padx=20, pady=(10, 0))
    
    tk.Label(opts, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
    count_var = tk.IntVar(value=p.get("count", 1))
    ttk.Spinbox(opts, from_=1, to=100, textvariable=count_var, width=10,
                validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
                
    tk.Label(opts, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
    delay_var = tk.IntVar(value=p.get("delay_after", 100))
    ttk.Spinbox(opts, from_=0, to=10000, textvariable=delay_var, width=10,
                validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)
                
    def apply():
        k = key_var.get().strip().lower()
        if not k:
            messagebox.showwarning("Warning", "Enter or capture a key / combo.", parent=popup)
            return
        try:
            count = max(1, int(count_var.get()))
            delay_after = max(0, int(delay_var.get()))
        except Exception:
            count, delay_after = 1, 100
        p["name"] = name_var.get().strip()
        p["key"] = k
        p["count"] = count
        p["delay_after"] = delay_after
        self.refresh_points_list()
        self.select_index(self.selected_index)
        self.status_label.config(text="Item updated", fg="#a6e3a1")
        popup.destroy()
        
    btn_row = tk.Frame(popup, bg="#1e1e2e")
    btn_row.pack(pady=12)
    ttk.Button(btn_row, text="Apply", command=apply, width=8).pack(side="left", padx=4)
    ttk.Button(btn_row, text="Cancel", command=popup.destroy, width=8).pack(side="left", padx=4)
    
    popup.update_idletasks()
    x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = self.root.winfo_y() + 100
    popup.geometry(f"+{x}+{y}")


def add_key_action(self):
    """Popup for adding a Keyboard Key / Combo action."""
    if self.is_busy():
        return
    popup = tk.Toplevel(self.root)
    popup.title("Add Keyboard Action")
    popup.configure(bg="#1e1e2e")
    popup.resizable(False, False)
    popup.transient(self.root)
    popup.grab_set()
    
    vcmd = (popup.register(self.validate_number), "%d", "%P")
    tk.Label(popup, text="Add Keyboard Action", font=("Segoe UI", 11, "bold"),
             bg="#1e1e2e", fg="#89b4fa").pack(pady=(12, 4))
    tk.Label(popup, text="Type manually or use Capture Key (Ctrl/Alt/Shift/Cmd + key)",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack()
             
    name_frame = tk.Frame(popup, bg="#1e1e2e")
    name_frame.pack(fill="x", padx=20, pady=(10, 0))
    tk.Label(name_frame, text="Name (optional):", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
    name_var = tk.StringVar(value="")
    ttk.Entry(name_frame, textvariable=name_var, width=18).pack(side="left", padx=(6, 0))
    
    key_row = tk.Frame(popup, bg="#1e1e2e")
    key_row.pack(fill="x", padx=20, pady=(10, 0))
    tk.Label(key_row, text="Key / Combo:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
    key_var = tk.StringVar(value="a")
    entry = ttk.Entry(key_row, textvariable=key_var, width=16, font=("Segoe UI", 10))
    entry.pack(side="left", padx=(6, 6))
    entry.focus_set()
    
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
        
    ttk.Button(key_row, text="Capture Key", command=capture_from_listener, width=12).pack(side="left")
    
    tk.Label(popup, text="Examples:  a  |  ctrl+c  |  shift+3  |  alt+F4  |  cmd+v",
             bg="#1e1e2e", fg="#6c7086", font=("Segoe UI", 8)).pack(pady=(4, 0))
             
    opts = tk.Frame(popup, bg="#1e1e2e")
    opts.pack(padx=20, pady=(10, 0))
    
    tk.Label(opts, text="Repeat:", bg="#1e1e2e", fg="#cdd6f4").grid(row=0, column=0, sticky="w", pady=2)
    count_var = tk.IntVar(value=1)
    ttk.Spinbox(opts, from_=1, to=100, textvariable=count_var, width=10,
                validate="key", validatecommand=vcmd).grid(row=0, column=1, pady=2, padx=5)
                
    tk.Label(opts, text="Delay Between Repeats (ms):", bg="#1e1e2e", fg="#cdd6f4").grid(row=1, column=0, sticky="w", pady=2)
    delay_var = tk.IntVar(value=100)
    ttk.Spinbox(opts, from_=0, to=10000, textvariable=delay_var, width=10,
                validate="key", validatecommand=vcmd).grid(row=1, column=1, pady=2, padx=5)
                
    def apply():
        k = key_var.get().strip().lower()
        if not k:
            messagebox.showwarning("Warning", "Enter or capture a key / combo.", parent=popup)
            return
        try:
            count = max(1, int(count_var.get()))
            delay_after = max(0, int(delay_var.get()))
        except Exception:
            count, delay_after = 1, 100
        self.points.append({
            "action": "key", "key": k,
            "count": count,
            "delay_after": delay_after,
            "name": name_var.get().strip()
        })
        self.refresh_points_list()
        self.select_index(len(self.points) - 1)
        self.status_label.config(text=f"Key '{k}' added", fg="#a6e3a1")
        popup.destroy()
        
    btn_row = tk.Frame(popup, bg="#1e1e2e")
    btn_row.pack(pady=12)
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
    if self.click_listener and self.click_listener.is_alive():
        try:
            self.click_listener.stop()
        except Exception:
            pass
    self.click_listener = None
    self.restore_after_capture()
    self.status_label.config(text="Set properties for the new point...", fg="#f9e2af")
    self.root.after(120, lambda: self.open_add_popup(action, data))

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

import json
import platform
import ctypes
import re
import urllib.request
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
from pynput.keyboard import Key, Listener as KeyboardListener
from utils import key_to_str

class ProfilesManager:
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

    def toggle_infinite(self):
        self.rep_spin.config(state="disabled" if self.infinite.get() else "normal")

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())

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

    def _parse_version(self, tag):
        nums = re.findall(r"\d+", str(tag))
        return tuple(int(n) for n in nums) if nums else (0,)

    def check_for_update(self):
        self.status_label.config(text="Checking for updates...", fg="#f9e2af")
        self.root.update_idletasks()
        
        def worker():
            try:
                url = "https://api.github.com/repos/tamimialiir/AutoClickerPro/releases/latest"
                req = urllib.request.Request(url, headers={"User-Agent": "AutoClickerPro"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                latest_tag = data.get("tag_name") or data.get("name") or ""
                releases_url = data.get("html_url") or f"{self.github_url}/releases"
                current = self._parse_version(self.version)
                latest = self._parse_version(latest_tag)
                
                def show_result():
                    if latest > current:
                        msg = f"A new version is available!\n\nCurrent:  {self.version}\nLatest:   {latest_tag}"
                        result = messagebox.askyesno("Update Available", msg + "\n\nOpen the Releases page to download?", parent=self.root)
                        if result:
                            webbrowser.open(releases_url)
                        self.status_label.config(text=f"Update available: {latest_tag}", fg="#a6e3a1")
                    else:
                        messagebox.showinfo("Up to Date", f"You are using the latest version ({self.version}).", parent=self.root)
                        self.status_label.config(text="You're up to date", fg="#a6e3a1")
                        
                self.root.after(0, show_result)
            except Exception as e:
                def show_err():
                    messagebox.showwarning("Update Check Failed", f"Could not check for updates.\n\n{e}", parent=self.root)
                    self.status_label.config(text="Update check failed", fg="#f38ba8")
                self.root.after(0, show_err)
                
        threading.Thread(target=worker, daemon=True).start()

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
                        
                    kstr_lower = kstr.lower().replace("key.", "").replace(" ", "_")
                    is_media = (
                        kstr_lower.startswith(("media_", "volume_", "brightness_", "launch_", "browser_"))
                        or any(s in kstr_lower for s in (
                            "volume_up", "volume_down", "volume_mute",
                            "play_pause", "next_track", "prev_track", "stop_media",
                            "media_play", "media_pause", "media_stop"
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

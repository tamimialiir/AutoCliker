import time
import tkinter as tk
from tkinter import messagebox
from pynput import mouse
from pynput.mouse import Button
from pynput.keyboard import Listener as KeyboardListener
from utils import key_to_str

class RecorderEngine:
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
        self.set_record_indicator(True)
        try:
            self.set_ui_lock_state("recording")
        except Exception:
            pass
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

        def rec_on_click(x, y, button, pressed):
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

        def rec_on_scroll(x, y, dx, dy):
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
                "action": "scroll", "x": cx_val, "y": cy_var, "dx": 0, "dy": int(dy),
                "count": 1, "delay_after": 30, "name": ""
            })
            return True

        def rec_on_press(key):
            if not self.is_recording:
                return False
            kstr = key_to_str(key, self._rec_held_mods)
            if kstr == self.record_stop_hotkey:
                self.root.after(0, lambda: self.stop_recording(from_ui=False))
                return False
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

        def rec_on_release(key):
            if not self.is_recording:
                return False
            try:
                name = key_to_str(key)
                if name in ("ctrl", "alt", "shift", "cmd"):
                    self._rec_held_mods.discard(name)
            except Exception:
                pass
            return True

        # Resolve scroll recording coords dynamically or using active position
        cx_val, cy_var = 0, 0
        def update_scroll_coords(x, y):
            nonlocal cx_val, cy_var
            cx_val, cy_var = x, y

        # Track last coordinates
        def track_move(x, y):
            update_scroll_coords(x, y)
            return True

        self.record_mouse_listener = mouse.Listener(on_click=rec_on_click, on_scroll=rec_on_scroll, on_move=track_move)
        self.record_mouse_listener.start()
        
        self.record_keyboard_listener = KeyboardListener(on_press=rec_on_press, on_release=rec_on_release)
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
                
        if from_ui:
            if self.record_events:
                # User clicked Stop Rec button on the UI.
                # Remove the last click action (the click on Stop Rec button itself)
                # and the wait action right before it.
                last_click_idx = None
                for i in range(len(self.record_events) - 1, -1, -1):
                    if self.record_events[i].get("action") == "click":
                        last_click_idx = i
                        break
                
                if last_click_idx is not None:
                    self.record_events.pop(last_click_idx)
                    wait_idx = last_click_idx - 1
                    if wait_idx >= 0 and self.record_events[wait_idx].get("action") == "wait":
                        self.record_events.pop(wait_idx)
        else:
            # Stopped by global hotkey
            if self.record_events and self.record_events[-1].get("action") == "key":
                k_val = self.record_events[-1].get("key", "")
                if k_val == self.record_stop_hotkey:
                    self.record_events.pop()
                    
        # Pop any trailing wait in either case
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
        self.set_record_indicator(False)
        try:
            self.set_ui_lock_state("stopped")
        except Exception:
            pass
        self.status_label.config(text=f"Recording stopped — {added} actions added", fg="#a6e3a1")

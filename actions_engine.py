import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode
from utils import parse_key_combo, str_to_key

class ActionsEngine:
    def get_safe_int(self, var, default, min_val=0, max_val=999999):
        try:
            return max(min_val, min(int(var.get()), max_val))
        except Exception:
            return default

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
            self.mouse.position = (sx + int((ex - sx) * t), sy + int((ey - sy) * t))
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
            pass

    def perform_scroll(self, p, pos_rand):
        x, y = self.apply_pos_random(p.get("x", 0), p.get("y", 0), pos_rand)
        self.mouse.position = (x, y)
        self.mouse.scroll(p.get("dx", 0), p.get("dy", 0))

    def click_loop(self, random_ms, pos_rand, cycles):
        cycle = 0
        if self.infinite.get():
            max_cycles = float("inf")
        else:
            max_cycles = cycles

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

                self.root.after(0, lambda idx=idx: self.highlight_current(idx))

                # Calculate progress percentage
                if not self.infinite.get():
                    total_steps = total_points * max_cycles
                    current_step_num = cycle * total_points + idx + 1
                    pct = int((current_step_num / total_steps) * 100)
                    prog = f"Cycle {cycle + 1}/{max_cycles}  |  Step {idx + 1}/{total_points}  |  {pct}%"
                else:
                    prog = f"Cycle {cycle + 1}  |  Step {idx + 1}/{total_points}"

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
                    if action == "wait":
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
        self.set_ui_lock_state("running")
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
            self.set_ui_lock_state("paused")
            self.status_label.config(text="Paused — edit list freely, then Resume", fg="#f9e2af")
        else:
            self.set_ui_lock_state("running")
            self.status_label.config(text="Running...", fg="#89b4fa")

    def on_clicking_finished(self):
        self.set_ui_lock_state("stopped")
        self.clear_highlight()
        self.status_label.config(text="Stopped", fg="#f38ba8")
        self.progress_label.config(text="")

    def stop_clicking(self):
        self.stop_flag = True
        self.is_paused = False  # unblock any wait_if_paused loops
        self.status_label.config(text="Stopping...", fg="#f9e2af")

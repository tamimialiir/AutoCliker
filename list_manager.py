import tkinter as tk
import copy
from utils import ACTION_COLORS

class ListManager:
    def bind_list_shortcuts(self):
        self.points_listbox.bind("<<ListboxSelect>>", self.on_point_select)
        self.points_listbox.bind("<Double-Button-1>", lambda e: self.open_edit_popup())
        self.points_listbox.bind("<ButtonPress-1>", self.on_list_drag_start)
        self.points_listbox.bind("<B1-Motion>", self.on_list_drag_motion)
        self.points_listbox.bind("<ButtonRelease-1>", self.on_list_drag_drop)
        
        self.points_listbox.bind("<Delete>", self.on_list_delete)
        self.root.bind("<Delete>", self.on_list_delete)
        
        for mod in ("Control", "Command"):
            self.root.bind(f"<{mod}-c>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-C>", lambda e: self.on_list_copy(e))
            self.root.bind(f"<{mod}-x>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-X>", lambda e: self.on_list_cut(e))
            self.root.bind(f"<{mod}-v>", lambda e: self.on_list_paste(e))
            self.root.bind(f"<{mod}-V>", lambda e: self.on_list_paste(e))

    def on_list_delete(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is not None:
            self.remove_point()
        return "break"

    def on_list_copy(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        self.clipboard_point = copy.deepcopy(self.points[self.selected_index])
        self.status_label.config(text="Item copied", fg="#a6e3a1")
        return "break"

    def on_list_cut(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.selected_index is None or self.selected_index >= len(self.points):
            return
        idx = self.selected_index
        self.clipboard_point = copy.deepcopy(self.points[idx])
        del self.points[idx]
        self.refresh_points_list()
        if self.points:
            self.select_index(min(idx, len(self.points) - 1))
        self.status_label.config(text="Item cut", fg="#f9e2af")
        return "break"

    def on_list_paste(self, event=None):
        if self.is_focus_on_input() or self.is_busy():
            return
        if self.clipboard_point is None:
            self.status_label.config(text="Clipboard empty", fg="#f38ba8")
            return "break"
        new_item = copy.deepcopy(self.clipboard_point)
        if self.selected_index is not None and 0 <= self.selected_index < len(self.points):
            insert_at = self.selected_index + 1
        else:
            insert_at = len(self.points)
        self.points.insert(insert_at, new_item)
        self.refresh_points_list()
        self.select_index(insert_at)
        self.status_label.config(text="Item pasted", fg="#a6e3a1")
        return "break"

    def on_list_drag_start(self, event):
        if self.is_busy():
            self.drag_start_index = None
            self.drag_current_index = None
            return
        index = self.points_listbox.nearest(event.y)
        if not (0 <= index < len(self.points)):
            self.drag_start_index = None
            self.drag_current_index = None
            return
        self.drag_start_index = index
        self.drag_current_index = index
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(index)
        self.points_listbox.activate(index)

    def on_list_drag_motion(self, event):
        if self.is_busy() or self.drag_start_index is None:
            return
        new_index = self.points_listbox.nearest(event.y)
        if new_index == self.drag_current_index or not (0 <= new_index < len(self.points)):
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

    def on_point_select(self, event=None):
        if self.is_busy():
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
            old_state = self.points_listbox.cget("state")
            if old_state == "disabled":
                self.points_listbox.config(state="normal")
            self.points_listbox.selection_clear(0, tk.END)
            if 0 <= index < self.points_listbox.size():
                self.points_listbox.selection_set(index)
                self.points_listbox.activate(index)
                self.points_listbox.see(index)
            if old_state == "disabled":
                self.points_listbox.config(state="disabled")
        except Exception:
            pass

    def clear_highlight(self):
        try:
            old_state = self.points_listbox.cget("state")
            if old_state == "disabled":
                self.points_listbox.config(state="normal")
            self.points_listbox.selection_clear(0, tk.END)
            if old_state == "disabled":
                self.points_listbox.config(state="disabled")
        except Exception:
            pass

    def refresh_points_list(self):
        try:
            old_state = self.points_listbox.cget("state")
            if old_state == "disabled":
                self.points_listbox.config(state="normal")
        except Exception:
            old_state = "normal"

        self.points_listbox.delete(0, tk.END)
        emoji_map = {
            "click":  "🖱️",
            "drag":   "↔️ ",
            "scroll": "↕️ ",
            "wait":   "⏱️  ",
            "key":    "⌨️  ",
        }
        for i, p in enumerate(self.points, 1):
            name = p.get("name", "").strip()
            action = p.get("action", "click")
            emoji = emoji_map.get(action, "🖱️ ")
            prefix = f"{i:02d}. {emoji}"
            if name:
                prefix += f"{name}: "
            
            if action == "drag":
                text = f"{prefix}DRAG ({p['x']},{p['y']}) → ({p['drag_x']},{p['drag_y']}) x{p.get('count', 1)}"
            elif action == "wait":
                text = f"{prefix}WAIT {p.get('delay', 500)}ms"
            elif action == "key":
                text = f"{prefix}KEY '{p.get('key', '?')}' x{p.get('count', 1)}"
            elif action == "scroll":
                direction = "UP" if p.get("dy", 0) > 0 else "DOWN"
                text = f"{prefix}SCROLL {direction} ({p.get('x', 0)},{p.get('y', 0)}) x{p.get('count', 1)}"
            else:
                text = f"{prefix}CLICK ({p['x']},{p['y']}) {p.get('type', 'Left')} x{p.get('count', 1)}"
                action = "click"
                
            self.points_listbox.insert(tk.END, text)
            idx = self.points_listbox.size() - 1
            color = ACTION_COLORS.get(action, "#cdd6f4")
            self.points_listbox.itemconfig(idx, foreground=color)

        try:
            if old_state == "disabled":
                self.points_listbox.config(state="disabled")
        except Exception:
            pass

    def select_index(self, index):
        if not self.points:
            self.selected_index = None
            self.edit_btn.config(state="disabled")
            self.points_listbox.selection_clear(0, tk.END)
            return
        index = max(0, min(index, len(self.points) - 1))
        self.selected_index = index
        self.points_listbox.selection_clear(0, tk.END)
        self.points_listbox.selection_set(index)
        self.points_listbox.activate(index)
        self.points_listbox.see(index)
        self.edit_btn.config(state="normal")

    def move_up(self):
        if self.selected_index is None or self.selected_index == 0 or self.is_busy():
            return
        i = self.selected_index
        self.points[i], self.points[i - 1] = self.points[i - 1], self.points[i]
        self.refresh_points_list()
        self.select_index(i - 1)

    def move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.points) - 1 or self.is_busy():
            return
        i = self.selected_index
        self.points[i], self.points[i + 1] = self.points[i + 1], self.points[i]
        self.refresh_points_list()
        self.select_index(i + 1)

    def remove_point(self):
        if self.is_busy() or self.selected_index is None:
            return
        idx = self.selected_index
        del self.points[idx]
        self.refresh_points_list()
        if self.points:
            self.select_index(min(idx, len(self.points) - 1))
        else:
            self.selected_index = None
            self.edit_btn.config(state="disabled")
        self.status_label.config(text="Point removed", fg="#f9e2af")

    def clear_points(self):
        if self.is_busy():
            return
        self.points.clear()
        self.selected_index = None
        self.edit_btn.config(state="disabled")
        self.refresh_points_list()
        self.status_label.config(text="All points cleared", fg="#f9e2af")

import sys
import os
import tkinter as tk
import platform
import importlib.util
from pynput.mouse import Controller as MouseController
from pynput.keyboard import Controller as KeyboardController

# Helper function for resource paths (works for dev and PyInstaller)
from utils import resource_path

# Generalized Dynamic Module Loader
def load_dynamic_module(module_name_in_sys, filenames):
    for name in filenames:
        path = name
        if not os.path.exists(path):
            dir_of_file = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(dir_of_file, name)
            
        if os.path.exists(path):
            try:
                m_name = name.split(".")[0].replace("-", "_")
                spec = importlib.util.spec_from_file_location(m_name, path)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name_in_sys] = module
                spec.loader.exec_module(module)
                return module
            except Exception as e:
                print(f"Error loading {path}: {e}")
                pass
    # Fallback to standard import
    try:
        module = __import__(module_name_in_sys)
        return module
    except ImportError:
        pass
    raise ImportError(f"Could not locate any of {filenames} or default {module_name_in_sys}")

# Dynamically load all components to support hyphenated files (-v2, -v3, -v4, etc.)
popups = load_dynamic_module("popups", ["popups-v2.py", "popups_v2.py", "popups.py"])
gui_components = load_dynamic_module("gui_components", ["gui_components-v3.py", "gui_components-v2.py", "gui_components.py"])
actions_engine = load_dynamic_module("actions_engine", ["actions_engine-v2.py", "actions_engine_v2.py", "actions_engine.py"])
recorder_engine = load_dynamic_module("recorder_engine", ["recorder_engine-v4.py", "recorder_engine-v3.py", "recorder_engine_v3.py", "recorder_engine-v2.py", "recorder_engine.py"])
gui_layout = load_dynamic_module("gui_layout", ["gui_layout-v6.py", "gui_layout-v5.py", "gui_layout-v4.py", "gui_layout-v3.py", "gui_layout.py"])
list_manager = load_dynamic_module("list_manager", ["list_manager-v3.py", "list_manager-v2.py", "list_manager_v2.py", "list_manager.py"])
profiles_manager = load_dynamic_module("profiles_manager", ["profiles_manager.py"])

# Extract parent classes
ActionsEngine = actions_engine.ActionsEngine
RecorderEngine = recorder_engine.RecorderEngine
GuiLayout = gui_layout.GuiLayout
ListManager = list_manager.ListManager
ProfilesManager = profiles_manager.ProfilesManager

class AutoClicker(ActionsEngine, ListManager, RecorderEngine, ProfilesManager, GuiLayout):
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Clicker Pro")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)
        self.version = "v5.2"
        self.github_url = "https://github.com/tamimialiir/AutoClickerPro"
        
        try:
            icon_path = resource_path("icon.png")
            self._app_icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self._app_icon)
        except Exception:
            pass
            
        # State variables
        self.points = []
        self.selected_index = None
        self.is_running = False
        self.is_paused = False
        self.stop_flag = False
        self.is_recording = False
        self.clipboard_point = None
        
        self.s_hotkey_enabled = tk.BooleanVar(value=True)
        self.g_hotkey_enabled = tk.BooleanVar(value=True)
        self.p_hotkey_enabled = tk.BooleanVar(value=True)
        self.rs_hotkey_enabled = tk.BooleanVar(value=True)
        self.re_hotkey_enabled = tk.BooleanVar(value=True)
        self.infinite = tk.BooleanVar(value=False)
        self.always_on_top = tk.BooleanVar(value=False)
        
        self.start_hotkey = "f1"
        self.pause_hotkey = "f2"
        self.stop_hotkey = "f3"
        self.record_start_hotkey = "f4"
        self.record_stop_hotkey = "f5"
        
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        self.click_listener = None
        self.keyboard_listener = None
        self.record_mouse_listener = None
        self.record_keyboard_listener = None
        
        self.waiting_for_hotkey = None
        self.adding_mode = None
        self.temp_drag_start = None
        self.record_events = []
        self.record_start_time = 0
        self.drag_start_index = None
        self.drag_current_index = None
        self.preview_windows = []
        
        self.force_english_keyboard()
        self.root.bind("<FocusIn>", lambda e: self.force_english_keyboard())
        
        self.setup_ui()
        self.bind_list_shortcuts()
        self.start_keyboard_listener()
        self.root.update_idletasks()
        
        width = 540
        height = self.root.winfo_reqheight()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = ((screen_height - height) // 2) - 30
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # Bind the external popup actions to subclass methods
    def open_add_popup(self, action, data):
        popups.open_add_popup(self, action, data)
        
    def open_edit_popup(self):
        popups.open_edit_popup(self)
        
    def _open_edit_key_popup(self, p):
        popups._open_edit_key_popup(self, p)
        
    def add_wait(self):
        popups.add_wait(self)
        
    def start_add_scroll(self):
        popups.start_add_scroll(self)
        
    def add_scroll_action(self, preset=None):
        popups.add_scroll_action(self, preset)
        
    def add_key_action(self):
        popups.add_key_action(self)
        
    def minimize_for_capture(self):
        popups.minimize_for_capture(self)
        
    def restore_after_capture(self):
        popups.restore_after_capture(self)
        
    def start_add_point(self, mode):
        popups.start_add_point(self, mode)
        
    def finish_add_point_and_edit(self, action, data):
        popups.finish_add_point_and_edit(self, action, data)

    # Previews delegates
    def clear_previews(self):
        gui_components.clear_previews(self.preview_windows)
        
    def show_point_preview(self, x, y, color="#f38ba8", label=""):
        return gui_components.show_point_preview(self.root, self.preview_windows, x, y, color, label)
        
    def _move_preview(self, preview_win, x_var, y_var):
        gui_components.move_preview(preview_win, x_var, y_var)
        
    def make_preview_draggable(self, preview_win, x_var, y_var):
        gui_components.make_preview_draggable(preview_win, x_var, y_var)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()

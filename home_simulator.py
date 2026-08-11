# home_simulator.py
import os
import tkinter as tk
import tkinter.font as tkfont
import math

try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "yuri_logo.png")

# Apple's San Francisco font isn't installed outside macOS, so this is a
# preference list: the first family Tk actually finds on the system wins.
_SF_FONT_STACK = [
    "SF Pro Display", "SF Pro Text", "SF Pro", ".SF NS Text",
    "Helvetica Neue", "Segoe UI", "Helvetica", "Arial",
]


def _resolve_sf_family(root):
    """Return the first available font family from the SF-like stack,
    querying Tk's actual installed font list."""
    available = set(tkfont.families(root))
    for family in _SF_FONT_STACK:
        if family in available:
            return family
    return "TkDefaultFont"


class SiriOrb:
    """Animated gradient-blob orb (Canvas-based), styled like Siri's listening
    indicator, in the app's black/turquoise palette."""

    STATE_COLORS = {
        "idle":      ["#1f2833", "#45a29e", "#0b0c10"],
        "listening": ["#66fcf1", "#45a29e", "#1f2833"],
        "thinking":  ["#45a29e", "#66fcf1", "#1f2833"],
        "speaking":  ["#66fcf1", "#c5c6c7", "#45a29e"],
    }
    STATE_ENERGY = {"idle": 0.12, "listening": 0.75, "thinking": 0.5, "speaking": 1.0}
    STATE_DELAY = {"idle": 60, "listening": 28, "thinking": 35, "speaking": 24}

    def __init__(self, parent, bg_color, size=140):
        self.size = size
        self.center = size / 2
        self.canvas = tk.Canvas(parent, width=size, height=size,
                                 bg=bg_color, highlightthickness=0)
        self.state = "idle"
        self.t = 0.0
        self._running = True
        self._after_id = None
        self._animate()

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def set_state(self, state):
        if state in self.STATE_COLORS:
            self.state = state

    def stop(self):
        self._running = False
        if self._after_id is not None:
            try:
                self.canvas.after_cancel(self._after_id)
            except tk.TclError:
                pass

    def _blob_points(self, cx, cy, base_r, phase, wobble, n=48):
        pts = []
        for i in range(n):
            ang = 2 * math.pi * i / n
            r = (base_r
                 + wobble * math.sin(ang * 3 + phase)
                 + wobble * 0.5 * math.sin(ang * 5 - phase * 1.7))
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return [c for p in pts for c in p]

    def _animate(self):
        if not self._running:
            return
        self.canvas.delete("all")

        colors = self.STATE_COLORS[self.state]
        energy = self.STATE_ENERGY[self.state]
        base_r = self.size * 0.28
        wobble = self.size * 0.06 * energy

        layer_defs = [
            (colors[2], 0.9, 0.62, 0.0),
            (colors[1], 0.7, 0.85, 2.1),
            (colors[0], 1.2, 1.00, 4.2),
        ]
        for color, speed, scale, phase_off in layer_defs:
            phase = self.t * speed + phase_off
            offset = self.size * 0.035 * energy
            cx = self.center + offset * math.cos(phase * 0.7)
            cy = self.center + offset * math.sin(phase * 0.9)
            pts = self._blob_points(cx, cy, base_r * scale, phase, wobble)
            self.canvas.create_polygon(pts, fill=color, outline="", smooth=True)

        core_r = base_r * 0.32 * (0.8 + 0.25 * energy)
        core_color = "#ffffff" if self.state == "speaking" else colors[0]
        self.canvas.create_oval(
            self.center - core_r, self.center - core_r,
            self.center + core_r, self.center + core_r,
            fill=core_color, outline=""
        )

        self.t += 0.05 + 0.10 * energy
        self._after_id = self.canvas.after(self.STATE_DELAY[self.state], self._animate)


class HouseView:
    """A simple 2D 'dollhouse cross-section' drawn on a Canvas."""

    WIDTH = 460
    HEIGHT = 320

    ROOF_APEX = (230, 15)
    ROOF_L = (50, 105)
    ROOF_R = (410, 105)
    BODY = (50, 105, 410, 300)
    DIVIDER_X = 230
    DIVIDER_Y_TOP = 105
    DIVIDER_Y_BOTTOM = 205
    LR_WINDOW = (80, 125, 125, 160)
    KIT_WINDOW = (335, 125, 380, 160)
    LR_LIGHT_C = (100, 245)
    KIT_LIGHT_C = (360, 245)
    AC_BOX = (285, 178, 400, 205)
    DOOR = (195, 205, 265, 300)

    def __init__(self, parent, theme):
        self.bg = theme["bg"]
        self.panel = theme["panel"]
        self.bright = theme["bright"]
        self.dark = theme["dark"]
        self.text_color = theme["text"]
        self.font = theme["font"]
        self.red = "#ff4c4c"

        self.canvas = tk.Canvas(parent, width=self.WIDTH, height=self.HEIGHT,
                                 bg=self.bg, highlightthickness=0)
        self._draw_static()

    def pack(self, **kwargs):
        self.canvas.pack(**kwargs)

    def _draw_static(self):
        c = self.canvas

        # Roof
        c.create_polygon(
            *self.ROOF_APEX, *self.ROOF_L, *self.ROOF_R,
            fill=self.dark, outline=self.bright, width=2
        )

        # Body
        x0, y0, x1, y1 = self.BODY
        c.create_rectangle(x0, y0, x1, y1, fill=self.panel, outline=self.bright, width=2)

        # Room divider
        c.create_line(self.DIVIDER_X, self.DIVIDER_Y_TOP,
                      self.DIVIDER_X, self.DIVIDER_Y_BOTTOM,
                      fill=self.dark, width=2, dash=(4, 3))

        # Windows
        for wx0, wy0, wx1, wy1 in (self.LR_WINDOW, self.KIT_WINDOW):
            c.create_rectangle(wx0, wy0, wx1, wy1, fill=self.bg, outline=self.dark, width=2)
            c.create_line((wx0 + wx1) / 2, wy0, (wx0 + wx1) / 2, wy1, fill=self.dark)
            c.create_line(wx0, (wy0 + wy1) / 2, wx1, (wy0 + wy1) / 2, fill=self.dark)

        # Room labels
        c.create_text(102, 115, text="LIVING ROOM", font=(self.font, 9, "bold"), fill=self.text_color)
        c.create_text(360, 115, text="KITCHEN", font=(self.font, 9, "bold"), fill=self.text_color)

        # Ground line
        c.create_line(20, y1, self.WIDTH - 20, y1, fill=self.dark, width=1)

    def update_devices(self, devices):
        c = self.canvas
        c.delete("dynamic")

        self._draw_light(self.LR_LIGHT_C, devices["living_room_light"]["status"] == "ON")
        self._draw_light(self.KIT_LIGHT_C, devices["kitchen_light"]["status"] == "ON")
        self._draw_ac(devices["ac"])
        self._draw_door(devices["door_lock"]["status"])

    def _draw_light(self, center, on):
        cx, cy = center
        c = self.canvas
        glow = self.bright if on else "#2a2e35"

        if on:
            c.create_oval(cx - 26, cy - 26, cx + 26, cy + 26, fill="#1c3937", outline="", tags="dynamic")
            c.create_oval(cx - 19, cy - 19, cx + 19, cy + 19, fill="#274d49", outline="", tags="dynamic")

        c.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, fill=glow, outline=self.dark, width=2, tags="dynamic")
        c.create_rectangle(cx - 5, cy + 11, cx + 5, cy + 17, fill="#555555", outline="", tags="dynamic")
        c.create_text(cx, cy + 32, text="ON" if on else "OFF",
                      font=(self.font, 9, "bold"), fill=glow, tags="dynamic")

    def _draw_ac(self, ac_data):
        x0, y0, x1, y1 = self.AC_BOX
        c = self.canvas
        on = ac_data["status"] == "ON"
        color = self.bright if on else "#2a2e35"

        c.create_rectangle(x0, y0, x1, y1, fill=self.panel, outline=color, width=2, tags="dynamic")
        span = x1 - x0 - 20
        for i in range(4):
            vx = x0 + 10 + i * (span / 3)
            c.create_line(vx, y0 + 6, vx, y1 - 6, fill=color, width=2, tags="dynamic")

        label = f"AC \u2022 {ac_data['temp']}\u00b0C" if on else "AC \u2022 OFF"
        c.create_text((x0 + x1) / 2, y1 + 13, text=label,
                      font=(self.font, 9, "bold"), fill=color, tags="dynamic")

    def _draw_door(self, status):
        x0, y0, x1, y1 = self.DOOR
        c = self.canvas
        locked = status == "LOCKED"
        color = self.red if locked else self.bright

        if locked:
            c.create_rectangle(x0, y0, x1, y1, fill="#33373d", outline=color, width=3, tags="dynamic")
            c.create_oval(x1 - 16, (y0 + y1) / 2 - 4, x1 - 8, (y0 + y1) / 2 + 4,
                          fill=color, outline="", tags="dynamic")
        else:
            c.create_rectangle(x0, y0, x1, y1, outline=color, width=2, dash=(3, 2), tags="dynamic")
            leaf_w = (x1 - x0) * 0.65
            c.create_polygon(
                x0, y0,
                x0 + leaf_w, y0 + 12,
                x0 + leaf_w, y1 - 12,
                x0, y1,
                fill=color, outline="", tags="dynamic"
            )

        px, py = (x0 + x1) / 2, y0 - 14
        c.create_rectangle(px - 8, py - 1, px + 8, py + 11, fill=color, outline="", tags="dynamic")
        if locked:
            c.create_arc(px - 6, py - 12, px + 6, py + 2, start=0, extent=180,
                         style="arc", outline=color, width=2, tags="dynamic")
        else:
            c.create_arc(px - 2, py - 14, px + 10, py, start=30, extent=180,
                         style="arc", outline=color, width=2, tags="dynamic")

        c.create_text((x0 + x1) / 2, y1 + 14, text=status,
                      font=(self.font, 9, "bold"), fill=color, tags="dynamic")


class HomeSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Apex Home Automations - Yuri Hub")
        self.root.geometry("560x820")
        
        # Color Theme: Black & Turquoise
        self.bg_color = "#0b0c10"       # Deep black background
        self.panel_color = "#1f2833"    # Dark gray for panels
        self.bright_accent = "#66fcf1"  # Bright Turquoise
        self.dark_accent = "#45a29e"    # Muted Turquoise
        self.text_color = "#c5c6c7"     # Light gray for standard text
        
        self.root.configure(bg=self.bg_color)

        self.font_family = _resolve_sf_family(self.root)
        
        # Device States
        self.devices = {
            "living_room_light": {"status": "OFF"},
            "kitchen_light": {"status": "OFF"},
            "ac": {"status": "OFF", "temp": 24},
            "door_lock": {"status": "LOCKED"},
        }
        
        self.create_widgets()

    def _display_name(self, device):
        if device == "ac":
            return "AC"
        return device.replace("_", " ").title()

    def create_widgets(self):
        title_font = (self.font_family, 18, "bold")
        normal_font = (self.font_family, 11)
        italic_font = (self.font_family, 10, "italic")

        # 1. Header Frame (Tightened padding)
        header_frame = tk.Frame(self.root, bg=self.bg_color)
        header_frame.pack(pady=(12, 0), fill="x")

        self._add_logo_or_title(header_frame, title_font)

        # 1b. Siri-style animated orb
        self.orb = SiriOrb(header_frame, bg_color=self.bg_color, size=140)
        self.orb.pack(pady=(4, 0))

        # 2. Transcription & Status Panel
        info_frame = tk.Frame(self.root, bg=self.panel_color, bd=2, relief="ridge")
        info_frame.pack(pady=8, padx=20, fill="x")
        
        self.status_label = tk.Label(info_frame, text="System Initializing...", font=italic_font, bg=self.panel_color, fg=self.text_color)
        self.status_label.pack(pady=(6, 0))
        
        self.transcription_label = tk.Label(
            info_frame, 
            text="Waiting for voice command...", 
            font=normal_font, 
            bg=self.panel_color, 
            fg=self.bright_accent, 
            wraplength=420, 
            justify="center"
        )
        self.transcription_label.pack(pady=(3, 10))

        # 3. House graphic
        house_frame = tk.Frame(self.root, bg=self.bg_color)
        house_frame.pack(pady=5, fill="both", expand=True)

        theme = {
            "bg": self.bg_color,
            "panel": self.panel_color,
            "bright": self.bright_accent,
            "dark": self.dark_accent,
            "text": self.text_color,
            "font": self.font_family,
        }
        self.house = HouseView(house_frame, theme)
        self.house.pack()
        self.house.update_devices(self.devices)

    def _add_logo_or_title(self, parent, title_font):
        """Display logo image with constrained maximum dimensions so it fits neatly as a header banner."""
        self.logo_image = None

        if os.path.exists(LOGO_PATH):
            try:
                # Set strict bounds for header logo so it never explodes vertical space
                max_w = 240
                max_h = 55

                if _PIL_AVAILABLE:
                    img = Image.open(LOGO_PATH).convert("RGBA")
                    scale = min(max_w / float(img.width), max_h / float(img.height))
                    target_w = max(1, int(img.width * scale))
                    target_h = max(1, int(img.height * scale))
                    img = img.resize((target_w, target_h), Image.LANCZOS)
                    self.logo_image = ImageTk.PhotoImage(img)
                else:
                    raw = tk.PhotoImage(file=LOGO_PATH)
                    factor_w = max(1, raw.width() // max_w)
                    factor_h = max(1, raw.height() // max_h)
                    factor = max(factor_w, factor_h)
                    self.logo_image = raw.subsample(factor, factor) if factor > 1 else raw

                tk.Label(parent, image=self.logo_image, bg=self.bg_color, bd=0).pack(pady=(0, 2))
                return
            except Exception:
                self.logo_image = None

        tk.Label(parent, text="YURI SMART HOME", font=title_font,
                 bg=self.bg_color, fg=self.bright_accent).pack(pady=(0, 2))

    def set_voice_state(self, state):
        self.orb.set_state(state)

    def shutdown(self):
        self.orb.stop()

    def update_status(self, message):
        if message.startswith("Heard:"):
            clean_text = message.replace("Heard: ", "")
            self.transcription_label.config(text=f'"{clean_text}"')
        else:
            self.status_label.config(text=message)
            
        self.root.update_idletasks()

    def execute_actions(self, actions_json):
        if 'actions' not in actions_json:
            return
            
        for action_data in actions_json['actions']:
            action = action_data.get('action')
            target = action_data.get('target')
            value = action_data.get('value')
            
            if target not in self.devices:
                continue

            data = self.devices[target]

            if target == "door_lock":
                if action in ("lock", "turn_on"):
                    data['status'] = "LOCKED"
                elif action in ("unlock", "turn_off"):
                    data['status'] = "UNLOCKED"

            elif target == "ac":
                if action == "turn_on":
                    data['status'] = "ON"
                elif action == "turn_off":
                    data['status'] = "OFF"
                elif action == "set_temperature" and value is not None:
                    data['temp'] = int(value)
                    data['status'] = "ON"

            else:  # lights
                if action == "turn_on":
                    data['status'] = "ON"
                elif action == "turn_off":
                    data['status'] = "OFF"

        self.house.update_devices(self.devices)

    def describe_actions(self, actions_json):
        phrases = []
        for action_data in actions_json.get('actions', []):
            action = action_data.get('action')
            target = action_data.get('target')
            value = action_data.get('value')

            if target not in self.devices:
                continue

            display_name = self._display_name(target)

            if target == "door_lock":
                if action in ("lock", "turn_on"):
                    phrases.append(f"{display_name} is now locked")
                elif action in ("unlock", "turn_off"):
                    phrases.append(f"{display_name} is now unlocked")
                else:
                    phrases.append(f"{display_name} updated")

            elif target == "ac":
                if action == "turn_on":
                    phrases.append(f"{display_name} is now on")
                elif action == "turn_off":
                    phrases.append(f"{display_name} is now off")
                elif action == "set_temperature" and value is not None:
                    phrases.append(f"{display_name} set to {value} degrees")
                else:
                    phrases.append(f"{display_name} updated")

            else:
                if action == "turn_on":
                    phrases.append(f"{display_name} is now on")
                elif action == "turn_off":
                    phrases.append(f"{display_name} is now off")
                else:
                    phrases.append(f"{display_name} updated")

        if not phrases:
            return "Done."
        if len(phrases) == 1:
            return phrases[0] + "."
        return ", ".join(phrases[:-1]) + ", and " + phrases[-1] + "."
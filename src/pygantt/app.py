import os
import sys
import subprocess
from math import sqrt
from datetime import datetime, timedelta, date
from calendar import monthrange
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Tree, Static, Input, Button, Label, TextArea

from .data import (
    load_projects,
    save_projects,
    add_project,
    add_task,
    update_task,
    delete_project,
    delete_task,
    export_projects_to_ods,
    get_export_project_names,
    sanitize_filename,
    ensure_ods_path,
)


THEMES = {
    "retro_neon": {
        "banner": "#ff3df5",
        "border_primary": "#00f0ff",
        "border_secondary": "#ff00d4",
        "task_bar_1": "#0b6ea8",
        "task_bar_2": "#1294d8",
        "current_day": "#39ff14",
        "text": "white",
        "background": "#000000",
        "accent_ok": "#39ff14",
        "accent_warn": "#ffea00",
        "accent_bad": "#ff5555",
        "project_header": "#00f0ff",
        "selection": "#ff00d4",
        "weekend_dim": "#1a1a1a",
    },
    "ice_neon": {
        "banner": "#6fffe9",
        "border_primary": "#6fffe9",
        "border_secondary": "#9b5de5",
        "task_bar_1": "#00bbf9",
        "task_bar_2": "#9b5de5",
        "current_day": "#39ff14",
        "text": "white",
        "background": "#000000",
        "accent_ok": "#39ff14",
        "accent_warn": "#ffea00",
        "accent_bad": "#ff5555",
        "project_header": "#6fffe9",
        "selection": "#9b5de5",
        "weekend_dim": "#1a1a1a",
    },
    "acid_green": {
        "banner": "#39ff14",
        "border_primary": "#39ff14",
        "border_secondary": "#ffea00",
        "task_bar_1": "#39ff14",
        "task_bar_2": "#ffea00",
        "current_day": "#ffffff",
        "text": "white",
        "background": "#000000",
        "accent_ok": "#39ff14",
        "accent_warn": "#ffea00",
        "accent_bad": "#ff5555",
        "project_header": "#39ff14",
        "selection": "#ffea00",
        "weekend_dim": "#1a1a1a",
    },
    "bw_night": {
        "banner": "white",
        "border_primary": "white",
        "border_secondary": "#bbbbbb",
        "task_bar_1": "white",
        "task_bar_2": "#999999",
        "current_day": "#39ff14",
        "text": "white",
        "background": "#000000",
        "accent_ok": "white",
        "accent_warn": "#bbbbbb",
        "accent_bad": "#777777",
        "project_header": "white",
        "selection": "#bbbbbb",
        "weekend_dim": "#1a1a1a",
    },
    "bw_day": {
        "banner": "black",
        "border_primary": "black",
        "border_secondary": "#666666",
        "task_bar_1": "black",
        "task_bar_2": "#666666",
        "current_day": "#00aa00",
        "text": "black",
        "background": "#ffffff",
        "accent_ok": "#006600",
        "accent_warn": "#666600",
        "accent_bad": "#aa0000",
        "project_header": "black",
        "selection": "#666666",
        "weekend_dim": "#dddddd",
    },
    "amber_term": {
        "banner": "#ffbf00",
        "border_primary": "#ffbf00",
        "border_secondary": "#ff9f1c",
        "task_bar_1": "#ffbf00",
        "task_bar_2": "#ff9f1c",
        "current_day": "#ffffff",
        "text": "#ffdf80",
        "background": "#120d00",
        "accent_ok": "#ffdf80",
        "accent_warn": "#ffbf00",
        "accent_bad": "#ff7b00",
        "project_header": "#ffbf00",
        "selection": "#ff9f1c",
        "weekend_dim": "#2a1d00",
    },
}


BASE_DIR = Path(__file__).resolve().parent
CUSTOM_BANNERS_FILE = BASE_DIR / "custom_banners.txt"

FALLBACK_BANNERS = [
    {
        "kind": "ascii",
        "name": "pygantt",
        "art": r"""
    ██████╗ ██╗   ██╗ ██████╗  █████╗ ███╗   ██╗████████╗████████╗
    ██╔══██╗╚██╗ ██╔╝██╔════╝ ██╔══██╗████╗  ██║╚══██╔══╝╚══██╔══╝
    ██████╔╝ ╚████╔╝ ██║  ███╗███████║██╔██╗ ██║   ██║      ██║
    ██╔═══╝   ╚██╔╝  ██║   ██║██╔══██║██║╚██╗██║   ██║      ██║
    ██║        ██║   ╚██████╔╝██║  ██║██║ ╚████║   ██║      ██║
    ╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝      ╚═╝
        """,
    }
]

LEFT_PANEL_WIDTH = 30
MONTHS_VISIBLE = 4
TIMELINE_CELL_WIDTH = 2


def load_custom_banners(file_path: str = CUSTOM_BANNERS_FILE) -> list[dict]:
    if not os.path.exists(file_path):
        return []

    banners: list[dict] = []
    current_name: str | None = None
    current_lines: list[str] = []

    with open(file_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")

            if line.startswith("===") and line.endswith("==="):
                if current_name and current_lines:
                    art = "\n".join(current_lines).rstrip()
                    if art.strip():
                        banners.append({"kind": "ascii", "name": current_name, "art": art})
                current_name = line.strip("= ").strip().lower()
                current_lines = []
            else:
                current_lines.append(line)

    if current_name and current_lines:
        art = "\n".join(current_lines).rstrip()
        if art.strip():
            banners.append({"kind": "ascii", "name": current_name, "art": art})

    return banners


def shorten_middle(value: str, max_length: int = 64) -> str:
    if len(value) <= max_length:
        return value
    if max_length < 10:
        return value[:max_length]
    left = (max_length - 3) // 2
    right = max_length - 3 - left
    return f"{value[:left]}...{value[-right:]}"


def auto_open_file(file_path: str | Path) -> None:
    path = str(file_path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


def task_status_label(task: dict) -> str:
    todos = task.get("todos", [])
    if todos and all(item.get("done", False) for item in todos):
        return "[OK]"
    if todos and any(item.get("done", False) for item in todos):
        return "[>>]"
    return "[--]"


def task_status_color(task: dict, theme: dict) -> str:
    todos = task.get("todos", [])
    if todos and all(item.get("done", False) for item in todos):
        return theme["accent_ok"]
    if todos and any(item.get("done", False) for item in todos):
        return theme["accent_warn"]
    return theme["text"]


def office_mode_for_file(file_path: str) -> str | None:
    ext = os.path.splitext(file_path)[1].lower()

    writer_exts = {".doc", ".docx", ".odt", ".rtf", ".txt", ".md"}
    calc_exts = {".xls", ".xlsx", ".ods", ".csv", ".tsv"}
    impress_exts = {".ppt", ".pptx", ".odp"}

    if ext in writer_exts:
        return "writer"
    if ext in calc_exts:
        return "calc"
    if ext in impress_exts:
        return "impress"
    return None


def retro_file_tag(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in {".doc", ".docx", ".odt", ".rtf"}:
        return "[W]"
    if ext in {".xls", ".xlsx", ".ods", ".csv", ".tsv"}:
        return "[C]"
    if ext in {".ppt", ".pptx", ".odp"}:
        return "[I]"
    if ext in {".txt", ".md"}:
        return "[T]"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return "[P]"
    if ext == ".pdf":
        return "[D]"
    return "[F]"


def pad_label(text: str, width: int = LEFT_PANEL_WIDTH) -> str:
    plain = text
    if len(plain) > width:
        plain = plain[: width - 3] + "..."
    return plain.ljust(width)


def make_color_cell(color: str) -> str:
    return f"[black on {color}]  [/]"


def render_color_grid(grid: list[list[str]]) -> str:
    return "\n".join("".join(make_color_cell(color) for color in row) for row in grid)


def make_blank_grid(width: int, height: int, color: str) -> list[list[str]]:
    return [[color for _ in range(width)] for _ in range(height)]


def fill_rect(grid: list[list[str]], x1: int, y1: int, x2: int, y2: int, color: str) -> None:
    height = len(grid)
    width = len(grid[0])
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(width, x2)
    y2 = min(height, y2)

    for y in range(y1, y2):
        for x in range(x1, x2):
            grid[y][x] = color


def point_in_triangle(px: float, py: float, a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    denom = ((b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1]))
    if denom == 0:
        return False

    w1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / denom
    w2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / denom
    w3 = 1 - w1 - w2
    return w1 >= 0 and w2 >= 0 and w3 >= 0


def draw_triangle(grid: list[list[str]], a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], color: str) -> None:
    height = len(grid)
    width = len(grid[0])

    min_x = max(0, int(min(a[0], b[0], c[0])))
    max_x = min(width - 1, int(max(a[0], b[0], c[0])) + 1)
    min_y = max(0, int(min(a[1], b[1], c[1])))
    max_y = min(height - 1, int(max(a[1], b[1], c[1])) + 1)

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if point_in_triangle(x + 0.5, y + 0.5, a, b, c):
                grid[y][x] = color


def draw_circle_ring(grid: list[list[str]], cx: float, cy: float, radius: float, thickness: float, color: str) -> None:
    height = len(grid)
    width = len(grid[0])

    inner = max(0.0, radius - thickness)
    outer = radius

    for y in range(height):
        for x in range(width):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            dist = sqrt(dx * dx + dy * dy)
            if inner <= dist <= outer:
                grid[y][x] = color


def draw_disc(grid: list[list[str]], cx: float, cy: float, radius: float, color: str) -> None:
    height = len(grid)
    width = len(grid[0])

    for y in range(height):
        for x in range(width):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            dist = sqrt(dx * dx + dy * dy)
            if dist <= radius:
                grid[y][x] = color


def draw_x_band(grid: list[list[str]], band_half_width: float, color: str) -> None:
    height = len(grid)
    width = len(grid[0])
    if width <= 1 or height <= 1:
        return

    slope = (height - 1) / (width - 1)

    for y in range(height):
        for x in range(width):
            d1 = abs(y - slope * x)
            d2 = abs(y - ((height - 1) - slope * x))
            if d1 <= band_half_width or d2 <= band_half_width:
                grid[y][x] = color


def build_progress_pride_flag(width: int = 44, height: int = 14) -> str:
    red = "#e40203"
    orange = "#ff8b00"
    yellow = "#fedf01"
    green = "#008127"
    blue = "#004dff"
    purple = "#760789"

    white = "#ffffff"
    pink = "#ff66ae"
    trans_blue = "#6cccff"
    brown = "#5b3715"
    black = "#000000"
    ring_purple = "#7b00a8"

    grid = make_blank_grid(width, height, red)

    stripe_colors = [red, orange, yellow, green, blue, purple]
    stripe_height = height / len(stripe_colors)

    for y in range(height):
        idx = min(len(stripe_colors) - 1, int(y / stripe_height))
        for x in range(width):
            grid[y][x] = stripe_colors[idx]

    chevrons = [
        (white, 0.0, 0.42),
        (pink, 0.0, 0.34),
        (trans_blue, 0.0, 0.26),
        (brown, 0.0, 0.18),
        (black, 0.0, 0.10),
    ]

    for color, left_offset, apex_ratio in chevrons:
        draw_triangle(
            grid,
            (left_offset, 0),
            (width * apex_ratio, height / 2),
            (left_offset, height),
            color,
        )

    draw_triangle(
        grid,
        (0, height * 0.15),
        (width * 0.12, height / 2),
        (0, height * 0.85),
        yellow,
    )

    draw_circle_ring(
        grid,
        cx=width * 0.08,
        cy=height / 2,
        radius=height * 0.18,
        thickness=height * 0.06,
        color=ring_purple,
    )

    return render_color_grid(grid)


def build_green_x_flag(width: int = 44, height: int = 14) -> str:
    dark_green = "#086224"
    bright_green = "#01a850"
    light_green = "#7ac043"
    cream = "#f2e9cc"

    grid = make_blank_grid(width, height, bright_green)

    draw_triangle(grid, (0, 0), (width, 0), (width / 2, height / 2), light_green)
    draw_triangle(grid, (0, height), (width, height), (width / 2, height / 2), light_green)

    draw_x_band(grid, band_half_width=2.2, color=dark_green)
    draw_x_band(grid, band_half_width=1.1, color=cream)

    return render_color_grid(grid)


def build_frisian_flag(width: int = 44, height: int = 14) -> str:
    blue = "#0000ff"
    white = "#ffffff"
    red = "#ff0000"

    grid = make_blank_grid(width, height, white)

    band = 2.0
    spacing = 6.0

    for y in range(height):
        for x in range(width):
            diagonal = (x + y) / spacing
            frac = diagonal - int(diagonal)
            if frac < (band / spacing):
                grid[y][x] = blue

    heart_positions = [
        (6, 3), (16, 5), (30, 2),
        (10, 9), (24, 8), (35, 6),
        (4, 7)
    ]

    for cx, cy in heart_positions:
        draw_disc(grid, cx, cy, 1.1, red)
        draw_triangle(grid, (cx - 0.8, cy + 0.2), (cx + 0.8, cy + 0.2), (cx, cy + 1.8), red)

        if 0 <= int(cx) < width and 0 <= int(cy) < height:
            grid[int(cy)][int(cx)] = white

    return render_color_grid(grid)


def build_palestine_flag(width: int = 44, height: int = 14) -> str:
    black = "#000000"
    white = "#ffffff"
    green = "#009639"
    red = "#ed2e38"

    grid = make_blank_grid(width, height, black)

    stripe_height = height // 3
    fill_rect(grid, 0, 0, width, stripe_height, black)
    fill_rect(grid, 0, stripe_height, width, stripe_height * 2, white)
    fill_rect(grid, 0, stripe_height * 2, width, height, green)

    draw_triangle(
        grid,
        (0, 0),
        (width * 0.33, height / 2),
        (0, height),
        red,
    )

    return render_color_grid(grid)


def build_png_flag(width: int = 44, height: int = 14) -> str:
    black = "#000000"
    red = "#c8102e"
    yellow = "#ffcd00"
    white = "#ffffff"

    grid = make_blank_grid(width, height, black)

    draw_triangle(grid, (0, 0), (width, 0), (width, height), red)

    star_positions = [(5, 9), (9, 7), (13, 9), (10, 11), (6, 12)]
    for cx, cy in star_positions:
        draw_disc(grid, cx, cy, 0.7, white)

    bird_points = [
        (24, 3), (27, 1), (31, 2), (33, 4), (31, 5), (28, 5),
        (26, 4), (25, 6), (28, 7), (31, 8), (29, 10), (27, 9),
        (26, 7), (24, 6), (22, 5), (23, 4)
    ]

    min_x = min(p[0] for p in bird_points)
    max_x = max(p[0] for p in bird_points)
    min_y = min(p[1] for p in bird_points)
    max_y = max(p[1] for p in bird_points)

    for y in range(min_y, max_y + 1):
        intersections = []
        for i in range(len(bird_points)):
            x1, y1 = bird_points[i]
            x2, y2 = bird_points[(i + 1) % len(bird_points)]
            if y1 == y2:
                continue
            if min(y1, y2) <= y < max(y1, y2):
                x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                intersections.append(x)

        intersections.sort()
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                x_start = int(intersections[i])
                x_end = int(intersections[i + 1])
                for x in range(x_start, x_end + 1):
                    if 0 <= x < width and 0 <= y < height:
                        grid[y][x] = yellow

    return render_color_grid(grid)


def build_flag_assets() -> list[dict]:
    return [
        {
            "kind": "flag",
            "name": "progress_pride",
            "art": build_progress_pride_flag(),
            "subtitle": "\nProgress Pride Flag",
        },
        {
            "kind": "flag",
            "name": "green_x",
            "art": build_green_x_flag(),
            "subtitle": "\nAchterhoek Flag",
        },
        {
            "kind": "flag",
            "name": "frisian",
            "art": build_frisian_flag(),
            "subtitle": "\nFrisian Flag",
        },
        {
            "kind": "flag",
            "name": "palestine",
            "art": build_palestine_flag(),
            "subtitle": "\nPalestine Flag",
        },
        {
            "kind": "flag",
            "name": "papua_new_guinea",
            "art": build_png_flag(),
            "subtitle": "\nPapua New Guinea Flag",
        },
    ]


class Banner(Static):
    def on_mount(self) -> None:
        self.refresh_banner()

    def refresh_banner(self) -> None:
        theme = self.app.theme_data
        banner_data = self.app.get_current_banner()

        default_subtitle = "    A Python-based terminal Gantt-chart tool, by Remie Stronks"
        subtitle = banner_data.get("subtitle", default_subtitle)

        art = banner_data.get("art", "").strip("\n")
        art_block = f"[{theme['banner']}]{art}[/]"

        self.update(
            "\n"
            f"{art_block}\n"
            f"[italic {theme['text']}]{subtitle}[/]\n"
        )

class ConfirmScreen(ModalScreen[bool]):
    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #dialog {
        width: 70;
        height: 11;
        padding: 1 2;
        border: round red;
        background: black;
        color: white;
    }
    #dialog_title {
        text-style: bold;
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
    }
    #dialog_message {
        content-align: center middle;
        height: 3;
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, title: str, message: str):
        super().__init__()
        self.title_text = title
        self.message_text = message

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.title_text, id="dialog_title")
            yield Label(self.message_text, id="dialog_message")
            with Horizontal(id="dialog_buttons"):
                yield Button("YES", variant="error", id="confirm")
                yield Button("NO", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


class AddProjectScreen(ModalScreen[str | None]):
    CSS = """
    AddProjectScreen {
        align: center middle;
    }
    #dialog {
        width: 60;
        height: 12;
        padding: 1 2;
        border: round cyan;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    #project_name_input {
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [("escape", "cancel_dialog", "CANCEL")]

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("ADD PROJECT", id="dialog_title")
            yield Input(placeholder="PROJECT NAME", id="project_name_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("CREATE", variant="success", id="create")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#project_name_input", Input).focus()

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        value = self.query_one("#project_name_input", Input).value.strip()
        self.dismiss(value if value else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value if value else None)


class TaskEditorScreen(ModalScreen[dict | None]):
    CSS = """
    TaskEditorScreen {
        align: center middle;
    }
    #dialog {
        width: 72;
        height: 22;
        padding: 1 2;
        border: round green;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    Input {
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [("escape", "cancel_dialog", "CANCEL")]

    def __init__(self, title: str = "ADD TASK", task_data: dict | None = None):
        super().__init__()
        self.dialog_title = title
        self.task_data = task_data or {}

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.dialog_title, id="dialog_title")
            yield Input(value=self.task_data.get("task", ""), placeholder="TASK NAME", id="task_name_input")
            yield Input(value=self.task_data.get("assignee", ""), placeholder="ASSIGNEE", id="assignee_input")
            yield Input(value=self.task_data.get("start", ""), placeholder="START DATE (YYYY-MM-DD)", id="start_input")
            yield Input(value=self.task_data.get("end", ""), placeholder="END DATE (YYYY-MM-DD)", id="end_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("SAVE", variant="success", id="save")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#task_name_input", Input).focus()

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        self.submit_task()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        current_id = event.input.id
        if current_id == "task_name_input":
            self.query_one("#assignee_input", Input).focus()
        elif current_id == "assignee_input":
            self.query_one("#start_input", Input).focus()
        elif current_id == "start_input":
            self.query_one("#end_input", Input).focus()
        elif current_id == "end_input":
            self.submit_task()

    def submit_task(self) -> None:
        task_name = self.query_one("#task_name_input", Input).value.strip()
        assignee = self.query_one("#assignee_input", Input).value.strip()
        start_raw = self.query_one("#start_input", Input).value.strip()
        end_raw = self.query_one("#end_input", Input).value.strip()

        if not task_name:
            self.app.notify("TASK NAME REQUIRED", severity="warning")
            return

        try:
            start = datetime.strptime(start_raw, "%Y-%m-%d")
            end = datetime.strptime(end_raw, "%Y-%m-%d")
        except ValueError:
            self.app.notify("USE YYYY-MM-DD", severity="warning")
            return

        if end < start:
            self.app.notify("END BEFORE START", severity="warning")
            return

        self.dismiss(
            {
                "task": task_name,
                "assignee": assignee,
                "start": start,
                "end": end,
            }
        )


class ExportScreen(ModalScreen[str | None]):
    CSS = """
    ExportScreen {
        align: center middle;
    }
    #dialog {
        width: 100;
        height: 15;
        padding: 1 2;
        border: round green;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    #dialog_help {
        height: 2;
        margin-bottom: 1;
        content-align: center middle;
    }
    #file_path_input {
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [("escape", "cancel_dialog", "CANCEL")]

    def __init__(self, suggested_path: str):
        super().__init__()
        self.suggested_path = suggested_path

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("EXPORT PROJECTS TO .ODS", id="dialog_title")
            yield Label("ENTER FULL FILE PATH", id="dialog_help")
            yield Input(value=self.suggested_path, placeholder="FULL EXPORT PATH", id="file_path_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("EXPORT", variant="success", id="export")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#file_path_input", Input).focus()

    def action_cancel_dialog(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        file_path = self.query_one("#file_path_input", Input).value.strip()
        self.dismiss(file_path if file_path else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        file_path = event.value.strip()
        self.dismiss(file_path if file_path else None)


class AttachFileScreen(ModalScreen[str | None]):
    CSS = """
    AttachFileScreen {
        align: center middle;
    }
    #dialog {
        width: 80;
        height: 12;
        padding: 1 2;
        border: round yellow;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        height: 1;
        margin-bottom: 1;
        text-style: bold;
    }
    #file_path_input {
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("ATTACH FILE BY PATH", id="dialog_title")
            yield Input(placeholder="FULL FILE PATH", id="file_path_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("ATTACH", variant="success", id="attach")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#file_path_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        file_path = self.query_one("#file_path_input", Input).value.strip()
        self.dismiss(file_path if file_path else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        file_path = event.value.strip()
        self.dismiss(file_path if file_path else None)


class AttachMethodScreen(ModalScreen[str | None]):
    CSS = """
    AttachMethodScreen {
        align: center middle;
    }
    #dialog {
        width: 56;
        height: 13;
        padding: 1 2;
        border: round green;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    #dialog_message {
        content-align: center middle;
        height: 2;
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 14;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("ATTACH FILE", id="dialog_title")
            yield Label("SELECT INPUT METHOD", id="dialog_message")
            with Horizontal(id="dialog_buttons"):
                yield Button("ENTER PATH", variant="success", id="path")
                yield Button("BROWSE", id="browse")
                yield Button("CANCEL", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "path":
            self.dismiss("path")
        elif event.button.id == "browse":
            self.dismiss("browse")


class AttachmentPickerScreen(ModalScreen[str | None]):
    CSS = """
    AttachmentPickerScreen {
        align: center middle;
    }
    #dialog {
        width: 90;
        height: 22;
        padding: 1 2;
        border: round cyan;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    #attachment_tree {
        height: 1fr;
        border: solid white;
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self, title: str, attachments: list[str]):
        super().__init__()
        self.dialog_title = title
        self.attachments = attachments

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.dialog_title, id="dialog_title")
            yield Tree("FILES", id="attachment_tree")
            with Horizontal(id="dialog_buttons"):
                yield Button("SELECT", variant="success", id="select")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        tree = self.query_one("#attachment_tree", Tree)
        root = tree.root
        root.expand()
        root.remove_children()

        for path in self.attachments:
            filename = os.path.basename(path) or path
            root.add(f"{retro_file_tag(path)} {filename}", data=path)

        if root.children:
            tree.select_node(root.children[0])
        tree.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        tree = self.query_one("#attachment_tree", Tree)
        node = tree.cursor_node
        if node and isinstance(node.data, str):
            self.dismiss(node.data)
        else:
            self.dismiss(None)


class FileBrowserScreen(ModalScreen[str | None]):
    CSS = """
    FileBrowserScreen {
        align: center middle;
    }
    #dialog {
        width: 116;
        height: 34;
        padding: 1 2;
        border: round yellow;
        background: $surface;
    }
    #dialog_title {
        content-align: center middle;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    #current_path {
        height: 2;
        margin-bottom: 1;
    }
    #filter_line {
        height: 2;
        margin-bottom: 1;
    }
    #browser_tree {
        height: 1fr;
        border: solid white;
        margin-bottom: 1;
    }
    #dialog_buttons {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 11;
    }
    """

    BINDINGS = [
        ("backspace", "go_up", "UP"),
        ("h", "toggle_hidden", "HIDDEN"),
        ("enter", "activate_selection", "OPEN/SELECT"),
    ]

    def __init__(self, start_path: str | None = None):
        super().__init__()
        if start_path and os.path.isdir(start_path):
            self.current_path = os.path.abspath(start_path)
        else:
            self.current_path = os.path.expanduser("~")
        self.show_hidden = False
        self.file_filter = "all"

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("RETRO FILE BROWSER", id="dialog_title")
            yield Static("", id="current_path")
            yield Static("", id="filter_line")
            yield Tree("FILES", id="browser_tree")
            with Horizontal(id="dialog_buttons"):
                yield Button("OPEN DIR", id="open_folder")
                yield Button("SELECT", variant="success", id="select")
                yield Button("UP", id="up")
                yield Button("HIDDEN", id="toggle_hidden")
                yield Button("FILTER", id="change_filter")
                yield Button("CANCEL", id="cancel")

    def on_mount(self) -> None:
        self.refresh_browser()
        self.query_one("#browser_tree", Tree).focus()

    def matches_filter(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        filter_groups = {
            "all": set(),
            "text": {".txt", ".md", ".rtf"},
            "pdf": {".pdf"},
            "images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
            "writer": {".doc", ".docx", ".odt"},
            "calc": {".xls", ".xlsx", ".ods", ".csv", ".tsv"},
            "impress": {".ppt", ".pptx", ".odp"},
        }

        if self.file_filter == "all":
            return True
        return ext in filter_groups.get(self.file_filter, set())

    def refresh_browser(self) -> None:
        path_label = self.query_one("#current_path", Static)
        filter_label = self.query_one("#filter_line", Static)
        hidden_text = "ON" if self.show_hidden else "OFF"

        path_label.update(f"[b]PATH :[/b] {shorten_middle(self.current_path, 96)}")
        filter_label.update(f"[b]HIDDEN :[/b] {hidden_text}    [b]FILTER :[/b] {self.file_filter.upper()}")

        tree = self.query_one("#browser_tree", Tree)
        root = tree.root
        root.remove_children()
        root.set_label(os.path.basename(self.current_path) or self.current_path)
        root.data = {"type": "folder", "path": self.current_path}
        root.expand()

        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            root.add("[D] ..", data={"type": "folder", "path": parent})

        try:
            entries = sorted(
                os.scandir(self.current_path),
                key=lambda entry: (not entry.is_dir(), entry.name.lower()),
            )
        except Exception as exc:
            self.app.notify(f"READ ERROR: {exc}", severity="error")
            entries = []

        for entry in entries:
            try:
                name = entry.name
                if not self.show_hidden and name.startswith("."):
                    continue

                if entry.is_dir():
                    root.add(f"[D] {name}", data={"type": "folder", "path": entry.path})
                else:
                    if not self.matches_filter(name):
                        continue
                    root.add(f"{retro_file_tag(entry.path)} {name}", data={"type": "file", "path": entry.path})
            except (PermissionError, OSError):
                continue

        if root.children:
            tree.select_node(root.children[0])

    def cycle_filter(self) -> None:
        filters = ["all", "text", "pdf", "images", "writer", "calc", "impress"]
        current_index = filters.index(self.file_filter)
        self.file_filter = filters[(current_index + 1) % len(filters)]
        self.refresh_browser()
        self.app.notify(f"FILTER = {self.file_filter.upper()}")

    def get_selected_node_data(self) -> dict | None:
        tree = self.query_one("#browser_tree", Tree)
        node = tree.cursor_node
        if node is None or not isinstance(node.data, dict):
            return None
        return node.data

    def action_go_up(self) -> None:
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self.refresh_browser()

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self.refresh_browser()

    def action_activate_selection(self) -> None:
        node_data = self.get_selected_node_data()
        if not node_data:
            return

        node_type = node_data.get("type")
        path = node_data.get("path")

        if node_type == "folder" and path:
            self.current_path = path
            self.refresh_browser()
        elif node_type == "file" and path:
            self.dismiss(path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        if event.button.id == "up":
            self.action_go_up()
            return

        if event.button.id == "toggle_hidden":
            self.action_toggle_hidden()
            return

        if event.button.id == "change_filter":
            self.cycle_filter()
            return

        node_data = self.get_selected_node_data()
        if not node_data:
            self.app.notify("NO ITEM SELECTED", severity="warning")
            return

        node_type = node_data.get("type")
        path = node_data.get("path")

        if event.button.id == "open_folder":
            if node_type == "folder" and path:
                self.current_path = path
                self.refresh_browser()
            else:
                self.app.notify("SELECT A DIRECTORY", severity="warning")
            return

        if event.button.id == "select":
            if node_type == "file" and path:
                self.dismiss(path)
            else:
                self.app.notify("SELECT A FILE", severity="warning")


class TaskWorkspaceScreen(ModalScreen[dict | None]):
    CSS = """
    TaskWorkspaceScreen {
        align: center middle;
    }

    #workspace_dialog {
        width: 140;
        height: 40;
        border: round green;
        background: $surface;
        padding: 1;
        layout: vertical;
    }

    #workspace_title {
        height: 3;
        padding: 1 2;
        border: round cyan;
        text-style: bold;
    }

    #workspace_main {
        height: 1fr;
    }

    #left_pane {
        width: 28%;
        border: solid magenta;
        padding: 1;
    }

    #right_pane {
        width: 72%;
        border: solid cyan;
        padding: 1;
    }

    #task_info {
        height: 8;
        margin-bottom: 1;
    }

    #todo_header {
        height: 2;
        margin-bottom: 1;
    }

    #todo_input {
        margin-bottom: 1;
    }

    #todo_tree {
        height: 1fr;
        border: solid white;
        margin-bottom: 1;
    }

    #todo_buttons {
        height: auto;
        margin-top: 1;
    }

    #notes_header {
        height: 2;
        margin-bottom: 1;
    }

    #notes_help {
        height: 2;
        margin-bottom: 1;
    }

    #notes_area {
        height: 1fr;
        border: solid white;
    }

    #workspace_buttons {
        height: 3;
        border: round green;
        align: center middle;
    }

    Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    BINDINGS = [
        ("escape", "cancel_workspace", "BACK"),
        ("ctrl+s", "save_workspace", "SAVE"),
        ("ctrl+t", "toggle_todo", "TOGGLE TODO"),
        ("ctrl+d", "delete_todo", "DELETE TODO"),
    ]

    def __init__(self, project_name: str, task_index: int, task: dict, focus_mode: str = "notes"):
        super().__init__()
        self.project_name = project_name
        self.task_index = task_index
        self.task_title = task["task"]
        self.assignee = task.get("assignee", "")
        self.start = task["start"]
        self.end = task["end"]
        self.notes = task.get("notes", "")
        self.focus_mode = focus_mode
        self.todos = [
            {"text": item.get("text", ""), "done": bool(item.get("done", False))}
            for item in task.get("todos", [])
        ]

    def compose(self) -> ComposeResult:
        header = (
            f"TASK WORKSPACE :: {self.project_name} / {self.task_title}  "
            f"({self.start.strftime('%Y-%m-%d')} -> {self.end.strftime('%Y-%m-%d')})"
        )

        with Container(id="workspace_dialog"):
            yield Static(header, id="workspace_title")

            with Horizontal(id="workspace_main"):
                with Vertical(id="left_pane"):
                    task_info = (
                        f"[b]{self.task_title}[/b]\n"
                        f"PROJECT  : {self.project_name}\n"
                        f"ASSIGNEE : {self.assignee or '-'}\n"
                        f"START    : {self.start.strftime('%Y-%m-%d')}\n"
                        f"END      : {self.end.strftime('%Y-%m-%d')}\n"
                        f"TODO     : {sum(1 for t in self.todos if t.get('done'))}/{len(self.todos)} DONE"
                    )
                    yield Static(task_info, id="task_info")
                    yield Static("TODO LIST", id="todo_header")
                    yield Input(placeholder="NEW TODO ITEM", id="todo_input")
                    yield Tree("TODO", id="todo_tree")
                    with Horizontal(id="todo_buttons"):
                        yield Button("ADD", id="add_todo", variant="success")
                        yield Button("TOGGLE", id="toggle_todo")
                        yield Button("DELETE", id="delete_todo")

                with Vertical(id="right_pane"):
                    yield Static("TASK NOTES / TEXT", id="notes_header")
                    yield Static("WRITE OR EDIT TEXT HERE. USE CTRL+S OR SAVE.", id="notes_help")
                    yield TextArea(id="notes_area")

            with Horizontal(id="workspace_buttons"):
                yield Button("SAVE", variant="success", id="save")
                yield Button("CLOSE", id="close")

    def on_mount(self) -> None:
        notes_area = self.query_one("#notes_area", TextArea)
        try:
            notes_area.load_text(self.notes)
        except Exception:
            try:
                notes_area.text = self.notes
            except Exception:
                pass

        self.refresh_todo_tree()

        if self.focus_mode == "todo":
            self.query_one("#todo_input", Input).focus()
        else:
            notes_area.focus()

    def refresh_todo_tree(self) -> None:
        tree = self.query_one("#todo_tree", Tree)
        root = tree.root
        root.remove_children()
        root.expand()

        for index, item in enumerate(self.todos):
            mark = "[X]" if item.get("done", False) else "[ ]"
            root.add(f"{mark} {item.get('text', '')}", data=index)

        if root.children:
            tree.select_node(root.children[0])

        task_info = (
            f"[b]{self.task_title}[/b]\n"
            f"PROJECT  : {self.project_name}\n"
            f"ASSIGNEE : {self.assignee or '-'}\n"
            f"START    : {self.start.strftime('%Y-%m-%d')}\n"
            f"END      : {self.end.strftime('%Y-%m-%d')}\n"
            f"TODO     : {sum(1 for t in self.todos if t.get('done'))}/{len(self.todos)} DONE"
        )
        self.query_one("#task_info", Static).update(task_info)

    def get_selected_todo_index(self) -> int | None:
        tree = self.query_one("#todo_tree", Tree)
        node = tree.cursor_node
        if node is None or not isinstance(node.data, int):
            return None
        return node.data

    def add_todo(self) -> None:
        input_widget = self.query_one("#todo_input", Input)
        text = input_widget.value.strip()
        if not text:
            self.notify("TODO TEXT REQUIRED", severity="warning")
            return

        self.todos.append({"text": text, "done": False})
        input_widget.value = ""
        self.refresh_todo_tree()

    def action_toggle_todo(self) -> None:
        index = self.get_selected_todo_index()
        if index is None:
            self.notify("SELECT A TODO ITEM", severity="warning")
            return

        self.todos[index]["done"] = not self.todos[index].get("done", False)
        self.refresh_todo_tree()

    def action_delete_todo(self) -> None:
        index = self.get_selected_todo_index()
        if index is None:
            self.notify("SELECT A TODO ITEM", severity="warning")
            return

        del self.todos[index]
        self.refresh_todo_tree()

    def action_save_workspace(self) -> None:
        self.save_and_close()

    def action_cancel_workspace(self) -> None:
        self.dismiss(None)

    def save_and_close(self) -> None:
        notes_area = self.query_one("#notes_area", TextArea)
        notes_text = getattr(notes_area, "text", "")
        self.dismiss({"notes": notes_text, "todos": self.todos})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "todo_input":
            self.add_todo()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save_and_close()
        elif event.button.id == "close":
            self.dismiss(None)
        elif event.button.id == "add_todo":
            self.add_todo()
        elif event.button.id == "toggle_todo":
            self.action_toggle_todo()
        elif event.button.id == "delete_todo":
            self.action_delete_todo()


class PyGanttApp(App):
    CSS = """
    Screen {
        layout: vertical;
        background: black;
    }

    #main {
        height: 1fr;
        padding: 0 1 1 1;
        background: black;
    }

    #banner {
        padding: 1 1 1 2;
        margin-bottom: 1;
        content-align: left middle;
    }

    #lower-panels {
        height: 1fr;
        align: center top;
        background: black;
    }

    #projects-panel {
        width: 34;
        min-width: 28;
        height: 1fr;
        border: solid white;
        margin-right: 1;
    }

    #projects {
        height: 1fr;
        border: none;
    }

    #date-panel {
        width: 32;
        min-width: 32;
        height: 1fr;
        border: solid magenta;
        margin-right: 1;
    }

    #date-labels-scroll {
        width: 1fr;
        height: 1fr;
        overflow-x: hidden;
        overflow-y: auto;
        border: none;
    }

    #date-labels {
        width: 30;
        padding: 1;
    }

    #timeline-panel {
        width: 1fr;
        min-width: 80;
        height: 1fr;
        border: solid cyan;
    }

    #gantt-timeline-scroll {
        width: 1fr;
        height: 1fr;
        overflow-x: auto;
        overflow-y: auto;
        border: none;
    }

    #gantt-timeline {
        width: auto;
        height: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "QUIT"),
        ("a", "add_project", "ADD PROJECT"),
        ("t", "add_task", "ADD TASK"),
        ("e", "edit_selected", "EDIT"),
        ("d", "delete_selected", "DELETE"),
        ("enter", "open_workspace", "TASK WORKSPACE"),
        ("m", "toggle_project_selection", "TOGGLE PROJECT"),
        ("[", "previous_gantt_month", "PREV VIEW"),
        ("]", "next_gantt_month", "NEXT VIEW"),
        ("0", "reset_gantt_month", "RESET VIEW"),
        ("p", "cycle_theme", "THEME"),
        ("l", "cycle_logo", "LOGO"),
        ("f", "attach_file", "ATTACH FILE"),
        ("o", "open_attachment", "OPEN FILE"),
        ("r", "remove_attachment", "REMOVE FILE"),
        ("x", "export_projects", "EXPORT ODS"),
    ]

    def __init__(self):
        super().__init__()
        self.projects = load_projects()
        self.selected_project: str | None = None
        self.selected_task_index: int | None = None
        self.selected_projects: set[str] = set()
        self.gantt_day_offset = 0
        self.last_browsed_path = os.path.expanduser("~")

        self.theme_names = list(THEMES.keys())
        self.theme_name = "retro_neon"
        self.theme_data = THEMES[self.theme_name]

        loaded_banners = load_custom_banners(CUSTOM_BANNERS_FILE)
        self.banners = loaded_banners if loaded_banners else FALLBACK_BANNERS

        self.banner_index = 0
        for i, banner in enumerate(self.banners):
            if banner.get("name", "").lower() == "pygantt":
                self.banner_index = i
                break

        for project_tasks in self.projects.values():
            for task in project_tasks:
                task.setdefault("attachments", [])
                task.setdefault("notes", "")
                task.setdefault("todos", [])

    def get_current_banner(self) -> dict:
        return self.banners[self.banner_index]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="main"):
            yield Banner(id="banner")

            with Horizontal(id="lower-panels"):
                with Vertical(id="projects-panel"):
                    yield Tree("PROJECTS", id="projects")

                with Vertical(id="date-panel"):
                    with ScrollableContainer(id="date-labels-scroll"):
                        yield Static(id="date-labels")

                with Vertical(id="timeline-panel"):
                    with ScrollableContainer(id="gantt-timeline-scroll"):
                        yield Static(id="gantt-timeline")

            yield Static("", id="bottom-spacer")

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_project_tree()
        self.apply_theme()
        self.refresh_gantt_view()

    def on_resize(self) -> None:
        self.refresh_gantt_view()

    def apply_theme(self) -> None:
        theme = self.theme_data

        self.styles.background = theme["background"]
        self.screen.styles.background = theme["background"]

        for widget_id in [
            "#banner",
            "#main",
            "#lower-panels",
            "#projects-panel",
            "#projects",
            "#date-panel",
            "#date-labels-scroll",
            "#date-labels",
            "#timeline-panel",
            "#gantt-timeline-scroll",
            "#gantt-timeline",
        ]:
            try:
                widget = self.query_one(widget_id)
                widget.styles.background = theme["background"]
                widget.styles.color = theme["text"]
            except Exception:
                pass

        self.query_one("#banner").styles.border = ("round", theme["border_primary"])
        self.query_one("#projects-panel").styles.border = ("solid", theme["border_primary"])
        self.query_one("#date-panel").styles.border = ("solid", theme["border_secondary"])
        self.query_one("#timeline-panel").styles.border = ("solid", theme["border_primary"])

        self.query_one("#banner", Banner).refresh_banner()

    def refresh_project_tree(self) -> None:
        tree = self.query_one("#projects", Tree)
        root = tree.root
        root.remove_children()

        for project_name in sorted(self.projects.keys()):
            tasks = self.projects[project_name]

            if project_name in self.selected_projects:
                project_label = f"[bold {self.theme_data['accent_ok']}][+][/bold {self.theme_data['accent_ok']}] {project_name}"
            else:
                project_label = f"[dim][ ][/] {project_name}"

            project_node = root.add(
                project_label,
                data={"type": "project", "project": project_name},
            )

            for index, task in enumerate(tasks):
                color = task_status_color(task, self.theme_data)
                status = task_status_label(task)
                task_label = f"[{color}]{status} {task['task']}[/]"
                project_node.add(
                    task_label,
                    data={
                        "type": "task",
                        "project": project_name,
                        "task_index": index,
                    },
                )

        root.expand()
        for node in root.children:
            node.expand()

    def get_selected_task(self) -> dict | None:
        if self.selected_project is None or self.selected_task_index is None:
            return None
        tasks = self.projects.get(self.selected_project, [])
        if 0 <= self.selected_task_index < len(tasks):
            return tasks[self.selected_task_index]
        return None

    def get_selected_projects_for_gantt(self) -> list[str]:
        if self.selected_projects:
            return sorted(self.selected_projects)
        if self.selected_project:
            return [self.selected_project]
        return []

    def get_base_gantt_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        selected_rows = []

        for project_name in self.get_selected_projects_for_gantt():
            for task in self.projects.get(project_name, []):
                selected_rows.append(task)

        if selected_rows:
            first_day = min(task["start"].date() for task in selected_rows)
        else:
            first_day = today

        start = first_day.replace(day=1)

        end_year = start.year
        end_month = start.month

        for _ in range(MONTHS_VISIBLE - 1):
            if end_month == 12:
                end_month = 1
                end_year += 1
            else:
                end_month += 1

        end = date(end_year, end_month, monthrange(end_year, end_month)[1])
        return start, end

    def get_gantt_visible_range(self) -> tuple[date, date]:
        start, end = self.get_base_gantt_range()
        if self.gantt_day_offset == 0:
            return start, end
        shift = timedelta(days=self.gantt_day_offset)
        return start + shift, end + shift

    def refresh_gantt_view(self) -> None:
        labels = self.query_one("#date-labels", Static)
        timeline = self.query_one("#gantt-timeline", Static)

        selected = self.get_selected_projects_for_gantt()
        start_date, end_date = self.get_gantt_visible_range()

        left_lines, right_lines = self.build_gantt_lines(
            selected_projects=selected,
            projects=self.projects,
            start_date=start_date,
            end_date=end_date,
        )

        labels.update("\n".join(left_lines))
        timeline.update("\n".join(right_lines))

    def build_gantt_lines(
        self,
        selected_projects: list[str],
        projects: dict[str, list[dict]],
        start_date: date,
        end_date: date,
    ) -> tuple[list[str], list[str]]:
        today = datetime.now().date()
        total_days = (end_date - start_date).days + 1
        days = [start_date + timedelta(days=i) for i in range(total_days)]
        theme = self.theme_data

        left_lines: list[str] = []
        right_lines: list[str] = []

        def fit(value: str) -> str:
            return f"{value[:TIMELINE_CELL_WIDTH]:^{TIMELINE_CELL_WIDTH}}"

        def grouped(values: list[str]) -> str:
            prev = None
            parts = []
            for value in values:
                shown = value if value != prev else ""
                parts.append(fit(shown))
                prev = value
            return " ".join(parts)

        def plain(values: list[str]) -> str:
            return " ".join(fit(value) for value in values)

        def bar(style: str, char: str = "█") -> str:
            return f"[{style}]{char * TIMELINE_CELL_WIDTH}[/]"

        def empty() -> str:
            return " " * TIMELINE_CELL_WIDTH

        def weekend_cell() -> str:
            return "░" * TIMELINE_CELL_WIDTH

        def separator_line() -> str:
            return "─" * max(20, len(plain([f"{d.day:02d}" for d in days])))

        def make_task_row(task_start: date, task_end: date, is_selected_task: bool, row_number: int) -> str:
            cells = []
            row_color = theme["task_bar_1"] if row_number % 2 == 0 else theme["task_bar_2"]

            for day_value in days:
                weekend = day_value.weekday() >= 5
                in_task = task_start <= day_value <= task_end
                is_today = day_value == today

                if in_task and is_selected_task and is_today:
                    cells.append(bar(f"bold {theme['current_day']}"))
                elif in_task and is_selected_task:
                    cells.append(bar(f"bold {theme['selection']}"))
                elif in_task and is_today:
                    cells.append(bar(f"bold {theme['current_day']}"))
                elif in_task:
                    cells.append(bar(f"bold {row_color}"))
                elif is_today:
                    cells.append(bar(f"bold {theme['current_day']}", "▒"))
                elif weekend:
                    cells.append(weekend_cell())
                else:
                    cells.append(empty())

            return " ".join(cells)

        def make_project_header_row() -> str:
            cells = []
            for day_value in days:
                if day_value == today:
                    cells.append(bar(f"bold {theme['current_day']}", "·"))
                elif day_value.weekday() >= 5:
                    cells.append(weekend_cell())
                else:
                    cells.append(empty())
            return " ".join(cells)

        year_values = [f"{d.year % 100:02d}" for d in days]
        month_values = [d.strftime("%m") for d in days]
        week_values = [f"{d.isocalendar().week:02d}" for d in days]
        date_values = [f"{d.day:02d}" for d in days]
        dow_values = [d.strftime("%a")[:2].upper() for d in days]

        left_lines += [
            pad_label("YEAR"),
            pad_label("MONTH"),
            pad_label("WEEK"),
            pad_label("DATE"),
            pad_label("DAY"),
        ]
        right_lines += [
            grouped(year_values),
            grouped(month_values),
            grouped(week_values),
            plain(date_values),
            plain(dow_values),
        ]

        left_lines.append("─" * LEFT_PANEL_WIDTH)
        right_lines.append(separator_line())

        if not selected_projects:
            left_lines.append(pad_label("NO TASKS SELECTED"))
            right_lines.append(" ".join(empty() for _ in days))
            return left_lines, right_lines

        global_row_counter = 0

        for project_name in selected_projects:
            project_tasks = projects.get(project_name, [])

            header_label = f"[bold {theme['project_header']}]■ {project_name}[/]"
            left_lines.append(header_label)
            right_lines.append(make_project_header_row())

            if not project_tasks:
                left_lines.append(pad_label("  (NO TASKS)"))
                right_lines.append(" ".join(empty() for _ in days))
                left_lines.append("")
                right_lines.append("")
                continue

            for task_index, task in enumerate(project_tasks):
                task_start = task["start"].date()
                task_end = task["end"].date()
                status = task_status_label(task)

                is_selected = (
                    self.selected_project == project_name
                    and self.selected_task_index == task_index
                )

                task_text = pad_label(f"  {status} {task['task']}")

                if is_selected:
                    left_lines.append(f"[bold reverse]{task_text}[/]")
                else:
                    left_lines.append(task_text)

                right_lines.append(
                    make_task_row(
                        task_start=task_start,
                        task_end=task_end,
                        is_selected_task=is_selected,
                        row_number=global_row_counter,
                    )
                )
                global_row_counter += 1

            left_lines.append("")
            right_lines.append("")

        return left_lines, right_lines

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not isinstance(data, dict):
            return

        node_type = data.get("type")
        if node_type == "project":
            self.selected_project = data["project"]
            self.selected_task_index = None
        elif node_type == "task":
            self.selected_project = data["project"]
            self.selected_task_index = data["task_index"]
        else:
            return

        self.refresh_gantt_view()

    def action_add_project(self) -> None:
        self.push_screen(AddProjectScreen(), self.handle_add_project)

    def handle_add_project(self, project_name: str | None) -> None:
        if not project_name:
            self.notify("PROJECT CANCELLED")
            return

        if not add_project(self.projects, project_name):
            self.notify("INVALID OR DUPLICATE PROJECT", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_project_tree()
        self.notify(f"PROJECT ADDED: {project_name}")

    def action_add_task(self) -> None:
        if not self.selected_project:
            self.notify("SELECT A PROJECT FIRST", severity="warning")
            return
        self.push_screen(TaskEditorScreen("ADD TASK"), self.handle_add_task)

    def handle_add_task(self, task_data: dict | None) -> None:
        if not task_data or not self.selected_project:
            self.notify("TASK CANCELLED")
            return

        ok = add_task(
            self.projects,
            self.selected_project,
            task_data["task"],
            task_data["assignee"],
            task_data["start"],
            task_data["end"],
        )

        if not ok:
            self.notify("ADD TASK FAILED", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify(f"TASK ADDED: {task_data['task']}")

    def action_edit_selected(self) -> None:
        task = self.get_selected_task()
        if not self.selected_project:
            self.notify("SELECT A PROJECT FIRST", severity="warning")
            return
        if not task:
            self.notify("SELECT A TASK TO EDIT", severity="warning")
            return

        prefilled = {
            "task": task["task"],
            "assignee": task.get("assignee", ""),
            "start": task["start"].strftime("%Y-%m-%d"),
            "end": task["end"].strftime("%Y-%m-%d"),
        }
        self.push_screen(TaskEditorScreen("EDIT TASK", prefilled), self.handle_edit_task)

    def handle_edit_task(self, task_data: dict | None) -> None:
        if not task_data:
            self.notify("EDIT CANCELLED")
            return

        if self.selected_project is None or self.selected_task_index is None:
            self.notify("NO TASK SELECTED", severity="warning")
            return

        ok = update_task(
            self.projects,
            self.selected_project,
            self.selected_task_index,
            task_data["task"],
            task_data["assignee"],
            task_data["start"],
            task_data["end"],
        )

        if not ok:
            self.notify("UPDATE FAILED", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify(f"TASK UPDATED: {task_data['task']}")

    def action_delete_selected(self) -> None:
        task = self.get_selected_task()

        if task and self.selected_project is not None:
            self.push_screen(
                ConfirmScreen("DELETE TASK", f"DELETE '{task['task']}' ?"),
                self.handle_delete_task,
            )
            return

        if self.selected_project:
            self.push_screen(
                ConfirmScreen("DELETE PROJECT", f"DELETE '{self.selected_project}' ?"),
                self.handle_delete_project,
            )
            return

        self.notify("SELECT A PROJECT OR TASK", severity="warning")

    def handle_delete_task(self, confirmed: bool) -> None:
        if not confirmed:
            self.notify("DELETE CANCELLED")
            return

        if self.selected_project is None or self.selected_task_index is None:
            self.notify("NO VALID TASK", severity="warning")
            return

        tasks = self.projects.get(self.selected_project, [])
        if not (0 <= self.selected_task_index < len(tasks)):
            self.notify("NO VALID TASK", severity="warning")
            return

        task_name = tasks[self.selected_task_index]["task"]
        delete_task(self.projects, self.selected_project, self.selected_task_index)

        if self.selected_project not in self.projects:
            removed_project = self.selected_project
            self.selected_project = None
            self.selected_task_index = None
            self.selected_projects.discard(removed_project)
            save_projects(self.projects)
            self.refresh_project_tree()
            self.refresh_gantt_view()
            self.notify(f"TASK '{task_name}' REMOVED / PROJECT EMPTY")
            return

        self.selected_task_index = None
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify(f"TASK REMOVED: {task_name}")

    def handle_delete_project(self, confirmed: bool) -> None:
        if not confirmed:
            self.notify("DELETE CANCELLED")
            return

        if not self.selected_project:
            return

        project_name = self.selected_project
        delete_project(self.projects, project_name)

        self.selected_project = None
        self.selected_task_index = None
        self.selected_projects.discard(project_name)
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify(f"PROJECT REMOVED: {project_name}")

    def open_workspace_with_focus(self, focus_mode: str = "notes") -> None:
        task = self.get_selected_task()
        if not task or self.selected_project is None or self.selected_task_index is None:
            self.notify("SELECT A TASK", severity="warning")
            return

        workspace = TaskWorkspaceScreen(
            self.selected_project,
            self.selected_task_index,
            task,
            focus_mode=focus_mode,
        )
        self.push_screen(workspace, self.handle_workspace_result)

    def action_open_workspace(self) -> None:
        self.open_workspace_with_focus("notes")

    def handle_workspace_result(self, result: dict | None) -> None:
        if not result:
            self.notify("WORKSPACE CLOSED")
            return

        task = self.get_selected_task()
        if not task:
            self.notify("TASK NO LONGER AVAILABLE", severity="warning")
            return

        task["notes"] = result.get("notes", "")
        task["todos"] = result.get("todos", [])
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify("TASK WORKSPACE SAVED")

    def action_attach_file(self) -> None:
        if not self.get_selected_task():
            self.notify("SELECT A TASK FIRST", severity="warning")
            return
        self.push_screen(AttachMethodScreen(), self.handle_attach_method)

    def handle_attach_method(self, method: str | None) -> None:
        if not method:
            self.notify("ATTACH CANCELLED")
            return

        if method == "path":
            self.push_screen(AttachFileScreen(), self.handle_attach_file)
        elif method == "browse":
            self.push_screen(FileBrowserScreen(self.last_browsed_path), self.handle_attach_file)

    def handle_attach_file(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("ATTACH CANCELLED")
            return

        normalized = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(normalized):
            self.notify(f"FILE NOT FOUND: {normalized}", severity="error")
            return
        if os.path.isdir(normalized):
            self.notify("SELECT A FILE, NOT A DIRECTORY", severity="warning")
            return

        task = self.get_selected_task()
        if not task:
            self.notify("NO TASK SELECTED", severity="warning")
            return

        self.last_browsed_path = os.path.dirname(normalized) or self.last_browsed_path
        attachments = task.setdefault("attachments", [])
        if normalized in attachments:
            self.notify("FILE ALREADY ATTACHED", severity="warning")
            return

        attachments.append(normalized)
        save_projects(self.projects)
        self.notify(f"ATTACHED: {os.path.basename(normalized)}")

    def action_open_attachment(self) -> None:
        task = self.get_selected_task()
        if not task:
            self.notify("SELECT A TASK FIRST", severity="warning")
            return

        attachments = task.get("attachments", [])
        if not attachments:
            self.notify("NO ATTACHMENTS", severity="warning")
            return

        if len(attachments) == 1:
            self.open_file_path(attachments[0])
            return

        self.push_screen(
            AttachmentPickerScreen("OPEN ATTACHMENT", attachments),
            self.handle_open_attachment_selection,
        )

    def handle_open_attachment_selection(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("OPEN CANCELLED")
            return
        self.open_file_path(file_path)

    def open_with_libreoffice_mode(self, file_path: str, mode: str) -> bool:
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["soffice", f"--{mode}", file_path])
            else:
                subprocess.Popen(["libreoffice", f"--{mode}", file_path])
            return True
        except FileNotFoundError:
            return False
        except Exception as exc:
            self.notify(f"LIBREOFFICE ERROR: {exc}", severity="error")
            return True

    def open_file_path(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            self.notify(f"FILE NOT FOUND: {file_path}", severity="error")
            return

        office_mode = office_mode_for_file(file_path)
        if office_mode is not None:
            opened = self.open_with_libreoffice_mode(file_path, office_mode)
            if opened:
                self.notify(f"OPENED IN {office_mode.upper()}: {os.path.basename(file_path)}")
                return

        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)

            self.notify(f"OPENED: {os.path.basename(file_path)}")
        except Exception as exc:
            self.notify(f"OPEN FAILED: {exc}", severity="error")

    def action_remove_attachment(self) -> None:
        task = self.get_selected_task()
        if not task:
            self.notify("SELECT A TASK FIRST", severity="warning")
            return

        attachments = task.get("attachments", [])
        if not attachments:
            self.notify("NO ATTACHMENTS", severity="warning")
            return

        if len(attachments) == 1:
            removed = attachments.pop()
            save_projects(self.projects)
            self.notify(f"REMOVED: {os.path.basename(removed)}")
            return

        self.push_screen(
            AttachmentPickerScreen("REMOVE ATTACHMENT", attachments),
            self.handle_remove_attachment_selection,
        )

    def handle_remove_attachment_selection(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("REMOVE CANCELLED")
            return

        task = self.get_selected_task()
        if not task:
            self.notify("NO TASK SELECTED", severity="warning")
            return

        attachments = task.get("attachments", [])
        if file_path not in attachments:
            self.notify("FILE NO LONGER ATTACHED", severity="warning")
            return

        attachments.remove(file_path)
        save_projects(self.projects)
        self.notify(f"REMOVED: {os.path.basename(file_path)}")

    def action_previous_gantt_month(self) -> None:
        start_date, end_date = self.get_base_gantt_range()
        screen_days = max(1, (end_date - start_date).days + 1)
        self.gantt_day_offset -= screen_days
        self.refresh_gantt_view()

    def action_next_gantt_month(self) -> None:
        start_date, end_date = self.get_base_gantt_range()
        screen_days = max(1, (end_date - start_date).days + 1)
        self.gantt_day_offset += screen_days
        self.refresh_gantt_view()

    def action_reset_gantt_month(self) -> None:
        self.gantt_day_offset = 0
        self.refresh_gantt_view()

    def action_cycle_theme(self) -> None:
        current_index = self.theme_names.index(self.theme_name)
        next_index = (current_index + 1) % len(self.theme_names)
        self.theme_name = self.theme_names[next_index]
        self.theme_data = THEMES[self.theme_name]
        self.apply_theme()
        self.refresh_project_tree()
        self.refresh_gantt_view()
        self.notify(f"THEME = {self.theme_name.upper()}")

    def action_cycle_logo(self) -> None:
        if not self.banners:
            return
        self.banner_index = (self.banner_index + 1) % len(self.banners)
        self.query_one("#banner", Banner).refresh_banner()
        current = self.get_current_banner()
        self.notify(f"DISPLAY = {current.get('name', 'UNKNOWN').upper()}")

    def toggle_project_in_gantt(self, project_name: str | None) -> None:
        if not project_name or project_name not in self.projects:
            self.notify("NO VALID PROJECT", severity="warning")
            return

        if project_name in self.selected_projects:
            self.selected_projects.remove(project_name)
            self.notify(f"REMOVED FROM GANTT: {project_name}")
        else:
            self.selected_projects.add(project_name)
            self.notify(f"ADDED TO GANTT: {project_name}")

        self.refresh_project_tree()
        self.refresh_gantt_view()

    def action_toggle_project_selection(self) -> None:
        tree = self.query_one("#projects", Tree)
        node = tree.cursor_node

        if node is None or not isinstance(node.data, dict):
            self.notify("SELECT A PROJECT OR TASK", severity="warning")
            return

        project_name = node.data.get("project")
        self.toggle_project_in_gantt(project_name)

    def action_export_projects(self) -> None:
        export_names = get_export_project_names(
            self.projects,
            self.selected_project,
            self.selected_projects,
        )

        if not export_names:
            self.notify("NO PROJECTS TO EXPORT", severity="warning")
            return

        if len(export_names) == 1:
            filename = sanitize_filename(export_names[0]) + ".ods"
        else:
            filename = f"pygantt_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ods"

        suggested_path = str(Path.home() / "Documents" / filename)
        self.push_screen(ExportScreen(suggested_path), self.handle_export_projects)

    def handle_export_projects(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("EXPORT CANCELLED")
            return

        export_names = get_export_project_names(
            self.projects,
            self.selected_project,
            self.selected_projects,
        )

        if not export_names:
            self.notify("NO PROJECTS TO EXPORT", severity="warning")
            return

        try:
            output_path = ensure_ods_path(file_path)
            saved_path = export_projects_to_ods(
                self.projects,
                export_names,
                output_path,
                self.theme_data,
            )
            self.notify(f"EXPORTED: {saved_path}")
            auto_open_file(saved_path)
        except Exception as exc:
            self.notify(f"EXPORT FAILED: {exc}", severity="error")


def main() -> None:
    PyGanttApp().run()


if __name__ == "__main__":
    main()

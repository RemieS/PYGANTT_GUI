from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import re

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell, TableColumn
from odf.text import P
from odf.style import (
    Style,
    TableCellProperties,
    TableColumnProperties,
    ParagraphProperties,
    TextProperties,
)

APP_NAME = "pygantt"


def get_data_dir() -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        data_dir = Path(xdg_data_home) / APP_NAME
    else:
        data_dir = Path.home() / ".local" / "share" / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


SAVE_FILE = get_data_dir() / "projects.json"


def sanitize_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*]+', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value[:120] if value else "pygantt_export"


def normalize_hex_color(value: str | None, fallback: str = "#000000") -> str:
    if not value:
        return fallback

    value = value.strip()

    named_colors = {
        "black": "#000000",
        "white": "#ffffff",
        "red": "#ff0000",
        "green": "#008000",
        "blue": "#0000ff",
        "yellow": "#ffff00",
        "magenta": "#ff00ff",
        "cyan": "#00ffff",
        "grey": "#808080",
        "gray": "#808080",
        "orange": "#ffa500",
        "purple": "#800080",
    }

    if value.lower() in named_colors:
        return named_colors[value.lower()]

    if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return value.lower()

    if re.fullmatch(r"#[0-9a-fA-F]{3}", value):
        return "#" + "".join(ch * 2 for ch in value[1:]).lower()

    return fallback


def ensure_json_path(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser()
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    return path


def ensure_ods_path(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser()
    if path.suffix.lower() != ".ods":
        path = path.with_suffix(".ods")
    return path


def serialize_projects(projects):
    serializable = {}
    for project_name, tasks in projects.items():
        serializable[project_name] = []
        for task in tasks:
            serializable[project_name].append(
                {
                    "task": task["task"],
                    "assignee": task.get("assignee", ""),
                    "start": task["start"].strftime("%Y-%m-%d"),
                    "end": task["end"].strftime("%Y-%m-%d"),
                }
            )
    return serializable


def deserialize_projects(data):
    projects = {}
    for project_name, tasks in data.items():
        projects[project_name] = []
        for task in tasks:
            projects[project_name].append(
                {
                    "task": task["task"],
                    "assignee": task.get("assignee", ""),
                    "start": datetime.strptime(task["start"], "%Y-%m-%d"),
                    "end": datetime.strptime(task["end"], "%Y-%m-%d"),
                }
            )
    return projects


def load_projects():
    if not SAVE_FILE.exists():
        return {}

    try:
        with SAVE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return deserialize_projects(data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {SAVE_FILE}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading projects: {e}")
        return {}


def save_projects(projects):
    with SAVE_FILE.open("w", encoding="utf-8") as f:
        json.dump(serialize_projects(projects), f, indent=4)


def import_projects_from_json(file_path: str | Path):
    path = Path(file_path).expanduser()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "projects" in data and isinstance(data["projects"], dict):
        return deserialize_projects(data["projects"])

    if isinstance(data, dict):
        return deserialize_projects(data)

    raise ValueError("Unsupported JSON format.")


def export_projects_to_json(projects, file_path: str | Path) -> Path:
    path = ensure_json_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump({"projects": serialize_projects(projects)}, f, indent=2)

    return path


def get_export_project_names(projects, selected_project=None, selected_projects=None):
    selected_projects = selected_projects or set()

    if selected_projects:
        return [name for name in sorted(selected_projects) if name in projects]
    if selected_project and selected_project in projects:
        return [selected_project]
    return sorted(projects.keys())


def get_export_date_range(projects, project_names):
    task_dates = []

    for project_name in project_names:
        for task in projects.get(project_name, []):
            task_dates.append((task["start"].date(), task["end"].date()))

    if not task_dates:
        return None

    start_date = min(item[0] for item in task_dates)
    end_date = max(item[1] for item in task_dates)
    return start_date, end_date


def export_projects_to_ods(
    projects,
    project_names,
    output_path: str | Path,
    theme: dict | None = None,
) -> Path:
    if not project_names:
        raise ValueError("No projects selected.")

    date_range = get_export_date_range(projects, project_names)
    if not date_range:
        raise ValueError("No tasks found.")

    theme = theme or {
        "border_primary": "#1f4e78",
        "border_secondary": "#d9eaf7",
        "task_bar_1": "#a9d18e",
        "task_bar_2": "#9fd5ff",
        "current_day": "#ffd966",
        "text": "#000000",
    }

    start_date, end_date = date_range

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)

    doc = OpenDocumentSpreadsheet()

    def make_cell_style(name: str, bg: str | None = None) -> Style:
        style = Style(name=name, family="table-cell")
        props = {
            "border": "0.02cm solid #888888",
            "verticalalign": "middle",
        }
        if bg:
            props["backgroundcolor"] = normalize_hex_color(bg)
        style.addElement(TableCellProperties(**props))
        doc.automaticstyles.addElement(style)
        return style

    def make_col_style(name: str, width: str) -> Style:
        style = Style(name=name, family="table-column")
        style.addElement(TableColumnProperties(columnwidth=width))
        doc.automaticstyles.addElement(style)
        return style

    def make_para_style(
        name: str,
        align: str = "left",
        bold: bool = False,
        color: str | None = None,
    ) -> Style:
        style = Style(name=name, family="paragraph")
        style.addElement(ParagraphProperties(textalign=align))
        text_args = {}
        if bold:
            text_args["fontweight"] = "bold"
        if color:
            text_args["color"] = normalize_hex_color(color, "#000000")
        if text_args:
            style.addElement(TextProperties(**text_args))
        doc.automaticstyles.addElement(style)
        return style

    header_bg = normalize_hex_color(theme.get("border_primary", "#1f4e78"), "#1f4e78")
    project_bg = normalize_hex_color(theme.get("border_secondary", "#d9eaf7"), "#d9eaf7")
    task_bg_1 = normalize_hex_color(theme.get("task_bar_1", "#a9d18e"), "#a9d18e")
    task_bg_2 = normalize_hex_color(theme.get("task_bar_2", "#9fd5ff"), "#9fd5ff")
    today_bg = normalize_hex_color(theme.get("current_day", "#ffd966"), "#ffd966")
    weekend_bg = "#eeeeee"
    text_color = normalize_hex_color(theme.get("text", "#000000"), "#000000")

    cell_default = make_cell_style("cell_default")
    cell_header = make_cell_style("cell_header", header_bg)
    cell_project = make_cell_style("cell_project", project_bg)
    cell_weekend = make_cell_style("cell_weekend", weekend_bg)
    cell_today = make_cell_style("cell_today", today_bg)
    cell_task_1 = make_cell_style("cell_task_1", task_bg_1)
    cell_task_2 = make_cell_style("cell_task_2", task_bg_2)

    col_project = make_col_style("col_project", "4.5cm")
    col_task = make_col_style("col_task", "4.5cm")
    col_assignee = make_col_style("col_assignee", "3.5cm")
    col_date = make_col_style("col_date", "1.3cm")

    para_left = make_para_style("para_left", "left", False, text_color)
    para_center = make_para_style("para_center", "center", False, text_color)
    para_header = make_para_style("para_header", "center", True, "#ffffff")
    para_project = make_para_style("para_project", "left", True, text_color)

    table = Table(name="Projects")

    table.addElement(TableColumn(stylename=col_project))
    table.addElement(TableColumn(stylename=col_task))
    table.addElement(TableColumn(stylename=col_assignee))
    for _ in dates:
        table.addElement(TableColumn(stylename=col_date))

    week_row = TableRow()
    for _ in range(3):
        cell = TableCell(stylename=cell_header)
        cell.addElement(P(stylename=para_header, text=""))
        week_row.addElement(cell)

    for d in dates:
        cell = TableCell(stylename=cell_header)
        cell.addElement(P(stylename=para_header, text=f"W{d.isocalendar().week:02d}"))
        week_row.addElement(cell)
    table.addElement(week_row)

    header_row = TableRow()
    for title in ["Project", "Task", "Assignee"]:
        cell = TableCell(stylename=cell_header)
        cell.addElement(P(stylename=para_header, text=title))
        header_row.addElement(cell)

    for d in dates:
        cell = TableCell(stylename=cell_header)
        cell.addElement(P(stylename=para_header, text=d.strftime("%Y-%m-%d")))
        header_row.addElement(cell)
    table.addElement(header_row)

    today = datetime.now().date()

    for project_name in project_names:
        tasks = projects.get(project_name, [])

        project_row = TableRow()

        c = TableCell(stylename=cell_project)
        c.addElement(P(stylename=para_project, text=project_name))
        project_row.addElement(c)

        for _ in range(2):
            c = TableCell(stylename=cell_project)
            c.addElement(P(stylename=para_center, text=""))
            project_row.addElement(c)

        for d in dates:
            style = cell_today if d == today else cell_project
            c = TableCell(stylename=style)
            c.addElement(P(stylename=para_center, text=""))
            project_row.addElement(c)

        table.addElement(project_row)

        for task_index, task in enumerate(tasks):
            row = TableRow()

            c = TableCell(stylename=cell_default)
            c.addElement(P(stylename=para_left, text=""))
            row.addElement(c)

            c = TableCell(stylename=cell_default)
            c.addElement(P(stylename=para_left, text=task["task"]))
            row.addElement(c)

            c = TableCell(stylename=cell_default)
            c.addElement(P(stylename=para_left, text=task.get("assignee", "")))
            row.addElement(c)

            active_style = cell_task_1 if task_index % 2 == 0 else cell_task_2
            task_start = task["start"].date()
            task_end = task["end"].date()

            for d in dates:
                if task_start <= d <= task_end:
                    style = cell_today if d == today else active_style
                elif d == today:
                    style = cell_today
                elif d.weekday() >= 5:
                    style = cell_weekend
                else:
                    style = cell_default

                c = TableCell(stylename=style)
                c.addElement(P(stylename=para_center, text=""))
                row.addElement(c)

            table.addElement(row)

    doc.spreadsheet.addElement(table)

    output_path = ensure_ods_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def add_project(projects, project_name):
    project_name = project_name.strip()
    if not project_name:
        return False
    if project_name in projects:
        return False
    projects[project_name] = []
    return True


def add_task(projects, project_name, task_name, assignee, start, end):
    if project_name not in projects:
        projects[project_name] = []
    projects[project_name].append(
        {
            "task": task_name,
            "assignee": assignee,
            "start": start,
            "end": end,
        }
    )


def update_task(projects, project_name, task_index, task_name, assignee, start, end):
    if project_name not in projects:
        return False

    tasks = projects[project_name]
    if not (0 <= task_index < len(tasks)):
        return False

    tasks[task_index] = {
        "task": task_name,
        "assignee": assignee,
        "start": start,
        "end": end,
    }
    return True


def delete_project(projects, project_name):
    if project_name in projects:
        del projects[project_name]
        return True
    return False


def delete_task(projects, project_name, task_index):
    if project_name not in projects:
        return False

    tasks = projects[project_name]
    if 0 <= task_index < len(tasks):
        del tasks[task_index]
        if not tasks:
            del projects[project_name]
        return True
    return False

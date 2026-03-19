import json
import re
from datetime import datetime, timedelta, date
from pathlib import Path

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

# IMPORTANT:
# Keep the data file next to the code/repository, like the older versions did.
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "projects.json"


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


def parse_task(raw: dict) -> dict:
    start = raw.get("start")
    end = raw.get("end")

    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d")
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d")

    return {
        "task": raw.get("task", "Untitled Task"),
        "assignee": raw.get("assignee", ""),
        "start": start,
        "end": end,
        "attachments": list(raw.get("attachments", [])),
        "notes": raw.get("notes", ""),
        "todos": [
            {
                "text": item.get("text", ""),
                "done": bool(item.get("done", False)),
            }
            for item in raw.get("todos", [])
        ],
    }


def serialize_task(task: dict) -> dict:
    return {
        "task": task["task"],
        "assignee": task.get("assignee", ""),
        "start": task["start"].strftime("%Y-%m-%d"),
        "end": task["end"].strftime("%Y-%m-%d"),
        "attachments": task.get("attachments", []),
        "notes": task.get("notes", ""),
        "todos": task.get("todos", []),
    }


def load_projects(file_path: str | Path | None = None) -> dict[str, list[dict]]:
    path = Path(file_path) if file_path else DATA_FILE

    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    # Support both:
    # {"projects": {...}}
    # and legacy flat {"Project A": [...]}
    if isinstance(data, dict) and "projects" in data and isinstance(data["projects"], dict):
        raw_projects = data["projects"]
    elif isinstance(data, dict):
        raw_projects = data
    else:
        return {}

    projects: dict[str, list[dict]] = {}
    for project_name, task_list in raw_projects.items():
        if not isinstance(task_list, list):
            continue
        projects[project_name] = [parse_task(task) for task in task_list]

    return projects


def save_projects(projects: dict[str, list[dict]], file_path: str | Path | None = None) -> None:
    path = Path(file_path) if file_path else DATA_FILE
    data = {
        "projects": {
            project_name: [serialize_task(task) for task in tasks]
            for project_name, tasks in projects.items()
        }
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def import_projects_from_json(file_path: str | Path) -> dict[str, list[dict]]:
    return load_projects(file_path)


def export_projects_to_json(
    projects: dict[str, list[dict]],
    file_path: str | Path,
) -> Path:
    path = ensure_json_path(file_path)
    data = {
        "projects": {
            project_name: [serialize_task(task) for task in tasks]
            for project_name, tasks in projects.items()
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def add_project(projects: dict[str, list[dict]], project_name: str) -> bool:
    project_name = project_name.strip()
    if not project_name or project_name in projects:
        return False
    projects[project_name] = []
    return True


def delete_project(projects: dict[str, list[dict]], project_name: str) -> bool:
    if project_name not in projects:
        return False
    del projects[project_name]
    return True


def add_task(
    projects: dict[str, list[dict]],
    project_name: str,
    task_name: str,
    assignee: str,
    start: datetime,
    end: datetime,
) -> bool:
    if project_name not in projects:
        return False

    projects[project_name].append(
        {
            "task": task_name,
            "assignee": assignee,
            "start": start,
            "end": end,
            "attachments": [],
            "notes": "",
            "todos": [],
        }
    )
    return True


def update_task(
    projects: dict[str, list[dict]],
    project_name: str,
    task_index: int,
    task_name: str,
    assignee: str,
    start: datetime,
    end: datetime,
) -> bool:
    if project_name not in projects:
        return False

    tasks = projects[project_name]
    if not (0 <= task_index < len(tasks)):
        return False

    existing = tasks[task_index]
    tasks[task_index] = {
        "task": task_name,
        "assignee": assignee,
        "start": start,
        "end": end,
        "attachments": existing.get("attachments", []),
        "notes": existing.get("notes", ""),
        "todos": existing.get("todos", []),
    }
    return True


def delete_task(projects: dict[str, list[dict]], project_name: str, task_index: int) -> bool:
    if project_name not in projects:
        return False

    tasks = projects[project_name]
    if not (0 <= task_index < len(tasks)):
        return False

    del tasks[task_index]
    if not tasks:
        del projects[project_name]
    return True


def get_export_project_names(
    projects: dict[str, list[dict]],
    selected_project: str | None,
    selected_projects: set[str],
) -> list[str]:
    if selected_projects:
        return [name for name in sorted(selected_projects) if name in projects]
    if selected_project and selected_project in projects:
        return [selected_project]
    return sorted(projects.keys())


def get_export_date_range(
    projects: dict[str, list[dict]],
    project_names: list[str],
) -> tuple[date, date] | None:
    task_dates: list[tuple[date, date]] = []

    for project_name in project_names:
        for task in projects.get(project_name, []):
            task_dates.append((task["start"].date(), task["end"].date()))

    if not task_dates:
        return None

    start_date = min(item[0] for item in task_dates)
    end_date = max(item[1] for item in task_dates)
    return start_date, end_date


def export_projects_to_ods(
    projects: dict[str, list[dict]],
    project_names: list[str],
    output_path: Path,
    theme: dict,
) -> Path:
    if not project_names:
        raise ValueError("No projects selected.")

    date_range = get_export_date_range(projects, project_names)
    if not date_range:
        raise ValueError("No tasks found.")

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
            c.addElement(P(stylename=para_left, text=task["assignee"]))
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
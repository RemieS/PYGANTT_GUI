from datetime import datetime
from pathlib import Path
import json
import os

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


def serialize_projects(projects):
    serializable = {}

    for project_name, tasks in projects.items():
        serializable[project_name] = []

        for task in tasks:
            serializable[project_name].append({
                "task": task["task"],
                "assignee": task["assignee"],
                "start": task["start"].strftime("%Y-%m-%d"),
                "end": task["end"].strftime("%Y-%m-%d"),
            })

    return serializable


def deserialize_projects(data):
    projects = {}

    for project_name, tasks in data.items():
        projects[project_name] = []

        for task in tasks:
            projects[project_name].append({
                "task": task["task"],
                "assignee": task["assignee"],
                "start": datetime.strptime(task["start"], "%Y-%m-%d"),
                "end": datetime.strptime(task["end"], "%Y-%m-%d"),
            })

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

    projects[project_name].append({
        "task": task_name,
        "assignee": assignee,
        "start": start,
        "end": end,
    })

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


import os
import sys
import subprocess
from datetime import datetime, timedelta, date
from calendar import monthrange

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Tree, Static, Input, Button, Label


from .data import (
    load_projects,
    save_projects,
    add_project,
    add_task,
    update_task,
    delete_project,
    delete_task,
)


THEMES = {
    "retro_neon": {
        "banner": "#ff3df5",
        "border_primary": "cyan",
        "border_secondary": "magenta",
        "border_task": "#ff00d4",
        "task_bar_1": "#ff00d4",
        "task_bar_2": "#00f0ff",
        "current_day": "#39ff14",
        "weekend_fill": "#444444",
        "text": "white",
        "background": "#000000",
    },
    "ice_neon": {
        "banner": "#6fffe9",
        "border_primary": "#6fffe9",
        "border_secondary": "#9b5de5",
        "border_task": "#00bbf9",
        "task_bar_1": "#00bbf9",
        "task_bar_2": "#9b5de5",
        "current_day": "#39ff14",
        "weekend_fill": "#3a3a3a",
        "text": "white",
        "background": "#000000",
    },
    "acid_neon": {
        "banner": "#39ff14",
        "border_primary": "#39ff14",
        "border_secondary": "#ffea00",
        "border_task": "#39ff14",
        "task_bar_1": "#39ff14",
        "task_bar_2": "#ffea00",
        "current_day": "#ffffff",
        "weekend_fill": "#444444",
        "text": "white",
        "background": "#000000",
    },
    "bw_night": {
        "banner": "white",
        "border_primary": "white",
        "border_secondary": "white",
        "border_task": "white",
        "task_bar_1": "white",
        "task_bar_2": "#999999",
        "current_day": "#39ff14",
        "weekend_fill": "#666666",
        "text": "white",
        "background": "#000000",
    },
    "bw_day": {
        "banner": "black",
        "border_primary": "black",
        "border_secondary": "black",
        "border_task": "black",
        "task_bar_1": "black",
        "task_bar_2": "#666666",
        "current_day": "#00aa00",
        "weekend_fill": "#bbbbbb",
        "text": "black",
        "background": "#ffffff",
    },
}


class Banner(Static):
    def on_mount(self) -> None:
        self.refresh_banner()

    def refresh_banner(self) -> None:
        banner = r"""
██████╗ ██╗   ██╗ ██████╗  █████╗ ███╗   ██╗████████╗████████╗
██╔══██╗╚██╗ ██╔╝██╔════╝ ██╔══██╗████╗  ██║╚══██╔══╝╚══██╔══╝
██████╔╝ ╚████╔╝ ██║  ███╗███████║██╔██╗ ██║   ██║      ██║
██╔═══╝   ╚██╔╝  ██║   ██║██╔══██║██║╚██╗██║   ██║      ██║
██║        ██║   ╚██████╔╝██║  ██║██║ ╚████║   ██║      ██║
╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝      ╚═╝
"""
        subtitle = "A Python-based retro Gantt chart tool, by Remie Stronks"
        theme_data = self.app.theme_data

        self.update(
            f"[bold underline {theme_data['banner']}]{banner}[/]\n"
            f"[italic {theme_data['text']}]{subtitle}[/]"
        )


class TaskDetails(Static):
    def show_task(self, task: dict | None) -> None:
        if not task:
            self.update("No task selected.")
            return

        attachments = task.get("attachments", [])
        attachment_text = "\n".join(f"- {path}" for path in attachments) if attachments else "None"

        self.update(
            f"[b]{task['task']}[/b]\n"
            f"Assignee: {task['assignee']}\n"
            f"Start: {task['start'].strftime('%Y-%m-%d')}\n"
            f"End: {task['end'].strftime('%Y-%m-%d')}\n"
            f"Attachments:\n{attachment_text}"
        )

    def show_project(self, project_name: str | None, tasks: list[dict] | None) -> None:
        if not project_name:
            self.update("No project selected.")
            return

        count = len(tasks or [])
        self.update(
            f"[b]{project_name}[/b]\n"
            f"Tasks: {count}\n"
            f"Use [b]t[/b] to add a task.\n"
            f"Select a task in the tree to view details."
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
        background: $surface;
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
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.title, id="dialog_title")
            yield Label(self.message, id="dialog_message")
            with Horizontal(id="dialog_buttons"):
                yield Button("Delete", variant="error", id="confirm")
                yield Button("Cancel", id="cancel")

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

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Add Project", id="dialog_title")
            yield Input(placeholder="Project name", id="project_name_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("Create", variant="success", id="create")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#project_name_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        project_name = self.query_one("#project_name_input", Input).value.strip()
        self.dismiss(project_name if project_name else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        project_name = event.value.strip()
        self.dismiss(project_name if project_name else None)


class TaskEditorScreen(ModalScreen[dict | None]):
    CSS = """
    TaskEditorScreen {
        align: center middle;
    }

    #dialog {
        width: 70;
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

    def __init__(self, title: str = "Add Task", task_data: dict | None = None):
        super().__init__()
        self.dialog_title = title
        self.task_data = task_data or {}

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(self.dialog_title, id="dialog_title")
            yield Input(
                value=self.task_data.get("task", ""),
                placeholder="Task name",
                id="task_name_input",
            )
            yield Input(
                value=self.task_data.get("assignee", ""),
                placeholder="Assignee",
                id="assignee_input",
            )
            yield Input(
                value=self.task_data.get("start", ""),
                placeholder="Start date (YYYY-MM-DD)",
                id="start_input",
            )
            yield Input(
                value=self.task_data.get("end", ""),
                placeholder="End date (YYYY-MM-DD)",
                id="end_input",
            )
            with Horizontal(id="dialog_buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#task_name_input", Input).focus()

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

        if not task_name or not assignee:
            self.app.notify("Task name and assignee are required.", severity="warning")
            return

        try:
            start = datetime.strptime(start_raw, "%Y-%m-%d")
            end = datetime.strptime(end_raw, "%Y-%m-%d")
        except ValueError:
            self.app.notify("Dates must use YYYY-MM-DD.", severity="warning")
            return

        if end < start:
            self.app.notify("End date cannot be earlier than start date.", severity="warning")
            return

        self.dismiss(
            {
                "task": task_name,
                "assignee": assignee,
                "start": start,
                "end": end,
            }
        )


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
            yield Label("Attach File", id="dialog_title")
            yield Input(placeholder="Full file path", id="file_path_input")
            with Horizontal(id="dialog_buttons"):
                yield Button("Attach", variant="success", id="attach")
                yield Button("Cancel", id="cancel")

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
            yield Tree("Attachments", id="attachment_tree")
            with Horizontal(id="dialog_buttons"):
                yield Button("Select", variant="success", id="select")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        tree = self.query_one("#attachment_tree", Tree)
        root = tree.root
        root.expand()

        for path in self.attachments:
            filename = os.path.basename(path) or path
            root.add(filename, data=path)

        if root.children:
            tree.select_node(root.children[0])
        tree.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        self.submit_selection()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            self.dismiss(event.node.data)

    def submit_selection(self) -> None:
        tree = self.query_one("#attachment_tree", Tree)
        node = tree.cursor_node

        if node is None:
            self.dismiss(None)
            return

        if isinstance(node.data, str):
            self.dismiss(node.data)
        else:
            self.dismiss(None)


class PyGanttApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }

    #banner {
        height: auto;
        padding: 1 2;
        border: round white;
        color: white;
    }

    #main {
        height: 1fr;
    }

    #sidebar {
        width: 30%;
        height: 1fr;
    }

    #projects {
        height: 1fr;
        border: solid white;
    }

    #right-pane {
        width: 70%;
        height: 1fr;
    }

    #details {
        height: 8;
        border: solid magenta;
        padding: 1;
    }

    #gantt-wrapper {
        height: 1fr;
    }

    #gantt-labels-scroll {
        width: 36;
        overflow-x: hidden;
        overflow-y: auto;
        border: solid cyan;
    }

    #gantt-timeline-scroll {
        width: 1fr;
        overflow-x: auto;
        overflow-y: auto;
        border: solid cyan;
    }

    #gantt-labels {
        width: 36;
        padding: 1;
    }

    #gantt-timeline {
        width: auto;
        height: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_project", "Add Project"),
        ("t", "add_task", "Add Task"),
        ("e", "edit_selected", "Edit"),
        ("d", "delete_selected", "Delete"),
        ("space", "toggle_project_selection", "Toggle Project"),
        ("[", "previous_gantt_month", "Prev View"),
        ("]", "next_gantt_month", "Next View"),
        ("0", "reset_gantt_month", "Reset View"),
        ("p", "cycle_theme", "Theme"),
        ("f", "attach_file", "Attach File"),
        ("o", "open_attachment", "Open File"),
        ("r", "remove_attachment", "Remove File"),
    ]

    def __init__(self):
        super().__init__()
        self.projects = load_projects()
        self.selected_project: str | None = None
        self.selected_task_index: int | None = None
        self.selected_projects: set[str] = set()
        self.gantt_day_offset = 0

        self.theme_names = list(THEMES.keys())
        self.theme_name = "retro_neon"
        self.theme_data = THEMES[self.theme_name]

        for project_tasks in self.projects.values():
            for task in project_tasks:
                task.setdefault("attachments", [])

    def compose(self) -> ComposeResult:
        yield Header()
        yield Banner(id="banner")

        with Horizontal(id="main"):
            with Vertical(id="sidebar"):
                yield Tree("Projects", id="projects")

            with Vertical(id="right-pane"):
                yield TaskDetails("No task selected.", id="details")

                with Horizontal(id="gantt-wrapper"):
                    with ScrollableContainer(id="gantt-labels-scroll"):
                        yield Static(id="gantt-labels")

                    with ScrollableContainer(id="gantt-timeline-scroll"):
                        yield Static(id="gantt-timeline")

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_project_tree()
        self.apply_theme()
        self.refresh_details()
        self.refresh_gantt_view()

    def on_resize(self) -> None:
        self.refresh_gantt_view()

    def apply_theme(self) -> None:
        theme_data = self.theme_data

        self.styles.background = theme_data["background"]

        self.query_one("#banner").styles.border = ("round", theme_data["border_primary"])
        self.query_one("#banner").styles.background = theme_data["background"]
        self.query_one("#banner").styles.color = theme_data["text"]

        self.query_one("#projects").styles.border = ("solid", theme_data["border_primary"])
        self.query_one("#projects").styles.background = theme_data["background"]
        self.query_one("#projects").styles.color = theme_data["text"]

        self.query_one("#details").styles.border = ("solid", theme_data["border_secondary"])
        self.query_one("#details").styles.background = theme_data["background"]
        self.query_one("#details").styles.color = theme_data["text"]

        self.query_one("#gantt-labels-scroll").styles.border = ("solid", theme_data["border_primary"])
        self.query_one("#gantt-labels-scroll").styles.background = theme_data["background"]
        self.query_one("#gantt-labels-scroll").styles.color = theme_data["text"]

        self.query_one("#gantt-timeline-scroll").styles.border = ("solid", theme_data["border_primary"])
        self.query_one("#gantt-timeline-scroll").styles.background = theme_data["background"]
        self.query_one("#gantt-timeline-scroll").styles.color = theme_data["text"]

        self.query_one("#gantt-labels").styles.background = theme_data["background"]
        self.query_one("#gantt-labels").styles.color = theme_data["text"]

        self.query_one("#gantt-timeline").styles.background = theme_data["background"]
        self.query_one("#gantt-timeline").styles.color = theme_data["text"]

        self.query_one("#banner", Banner).refresh_banner()
        self.refresh_details()
        self.refresh_gantt_view()

    def refresh_project_tree(self) -> None:
        tree = self.query_one("#projects", Tree)
        tree.clear()
        root = tree.root

        for project_name, tasks in self.projects.items():
            label = f"✔ {project_name}" if project_name in self.selected_projects else project_name
            project_node = root.add(label, data={"type": "project", "project": project_name})

            for index, task in enumerate(tasks):
                task_label = f"• {task['task']}"
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

    def refresh_details(self) -> None:
        details = self.query_one("#details", TaskDetails)

        if self.selected_project and self.selected_task_index is not None:
            task = self.get_selected_task()
            details.show_task(task)
        elif self.selected_project:
            details.show_project(self.selected_project, self.projects.get(self.selected_project, []))
        else:
            details.show_task(None)

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

    def refresh_gantt_view(self) -> None:
        labels = self.query_one("#gantt-labels", Static)
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

        scroll = self.query_one("#gantt-timeline-scroll", ScrollableContainer)
        available_width = max(20, scroll.size.width - 4)
        cell_width = max(2, min(6, available_width // max(1, total_days) - 1))

        left_lines: list[str] = []
        right_lines: list[str] = []
        theme_data = self.theme_data

        def fit(value: str) -> str:
            value = value[:cell_width]
            return f"{value:^{cell_width}}"

        def grouped(values: list[str]) -> str:
            prev = None
            cells = []
            for value in values:
                shown = value if value != prev else ""
                cells.append(fit(shown))
                prev = value
            return "│".join(cells)

        def plain(values: list[str]) -> str:
            return "│".join(fit(value) for value in values)

        def bar(style: str, char: str = "█") -> str:
            return f"[{style}]{char * cell_width}[/]"

        def empty() -> str:
            return " " * cell_width

        def weekend_cell() -> str:
            return fit("░" * cell_width)

        def make_task_row(row: dict, is_selected: bool, row_number: int) -> str:
            cells = []
            row_color = theme_data["task_bar_1"] if row_number % 2 == 0 else theme_data["task_bar_2"]

            for day_value in days:
                weekend = day_value.weekday() >= 5
                in_task = row["start"] <= day_value <= row["end"]
                is_today = day_value == today

                if in_task and is_selected and is_today:
                    cells.append(bar(f"bold {theme_data['current_day']}", "█"))
                elif in_task and is_selected:
                    cells.append(bar(f"bold {theme_data['border_secondary']}", "█"))
                elif in_task and is_today:
                    cells.append(bar(f"bold {theme_data['current_day']}", "█"))
                elif in_task:
                    cells.append(bar(f"bold {row_color}", "█"))
                elif is_today:
                    cells.append(bar(f"bold {theme_data['current_day']}", "▓"))
                elif weekend:
                    cells.append(weekend_cell())
                else:
                    cells.append(empty())

            return "│".join(cells)

        def make_project_row(project_start: date, project_end: date) -> str:
            cells = []
            for day_value in days:
                weekend = day_value.weekday() >= 5
                in_project = project_start <= day_value <= project_end
                is_today = day_value == today

                if in_project and is_today:
                    cells.append(bar(f"bold {theme_data['current_day']}", "▓"))
                elif in_project:
                    cells.append(bar(f"bold {theme_data['border_secondary']}", "▓"))
                elif is_today:
                    cells.append(bar(f"bold {theme_data['current_day']}", "▒"))
                elif weekend:
                    cells.append(weekend_cell())
                else:
                    cells.append(empty())

            return "│".join(cells)

        year_values = [f"{d.year % 100:02d}" for d in days]
        month_values = [d.strftime("%b")[:2] for d in days]
        week_values = [f"{d.isocalendar().week:02d}" for d in days]
        date_values = [f"{d.day:02d}" for d in days]
        dow_values = [d.strftime("%a")[:2] for d in days]

        left_lines += ["Year", "Month", "Week", "Date", "Day"]
        right_lines += [
            grouped(year_values),
            grouped(month_values),
            grouped(week_values),
            plain(date_values),
            plain(dow_values),
        ]

        left_lines.append("─" * 24)
        right_lines.append("─" * ((cell_width + 1) * total_days - 1))

        if not selected_projects:
            left_lines.append("No tasks planned")
            right_lines.append("│".join(empty() for _ in days))
            return left_lines, right_lines

        has_any_rows = False

        for project_name in selected_projects:
            project_tasks = projects.get(project_name, [])
            if not project_tasks:
                continue

            has_any_rows = True

            project_start = min(task["start"].date() for task in project_tasks)
            project_end = max(task["end"].date() for task in project_tasks)

            left_lines.append(f"[bold]{project_name}[/]")
            right_lines.append(make_project_row(project_start, project_end))

            for task_index, task in enumerate(project_tasks):
                row = {
                    "project": project_name,
                    "task": task["task"],
                    "assignee": task["assignee"],
                    "start": task["start"].date(),
                    "end": task["end"].date(),
                }

                label = f"  • {row['task']}"
                is_selected = (
                    self.selected_project == project_name
                    and self.selected_task_index == task_index
                )

                if is_selected:
                    left_lines.append(f"[bold reverse]{label}[/]")
                else:
                    left_lines.append(label)

                right_lines.append(make_task_row(row, is_selected, task_index))

        if not has_any_rows:
            left_lines.append("No tasks planned")
            right_lines.append("│".join(empty() for _ in days))

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

        self.refresh_details()
        self.refresh_gantt_view()

    def action_add_project(self) -> None:
        self.push_screen(AddProjectScreen(), self.handle_add_project)

    def handle_add_project(self, project_name: str | None) -> None:
        if not project_name:
            self.notify("Project creation cancelled.")
            return

        created = add_project(self.projects, project_name)

        if not created:
            self.notify("Project name is empty or already exists.", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_project_tree()
        self.notify(f"Project '{project_name.strip()}' added.")

    def action_add_task(self) -> None:
        if not self.selected_project:
            self.notify("Select a project first.", severity="warning")
            return

        self.push_screen(TaskEditorScreen("Add Task"), self.handle_add_task)

    def handle_add_task(self, task_data: dict | None) -> None:
        if not task_data or not self.selected_project:
            self.notify("Task creation cancelled.")
            return

        add_task(
            self.projects,
            self.selected_project,
            task_data["task"],
            task_data["assignee"],
            task_data["start"],
            task_data["end"],
        )

        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_details()
        self.refresh_gantt_view()
        self.notify(f"Task '{task_data['task'].strip()}' added to '{self.selected_project}'.")

    def action_edit_selected(self) -> None:
        task = self.get_selected_task()

        if not self.selected_project:
            self.notify("Select a project first.", severity="warning")
            return

        if not task:
            self.notify("Select a task in the tree to edit.", severity="warning")
            return

        prefilled = {
            "task": task["task"],
            "assignee": task["assignee"],
            "start": task["start"].strftime("%Y-%m-%d"),
            "end": task["end"].strftime("%Y-%m-%d"),
        }

        self.push_screen(
            TaskEditorScreen("Edit Task", prefilled),
            self.handle_edit_task,
        )

    def handle_edit_task(self, task_data: dict | None) -> None:
        if not task_data:
            self.notify("Edit cancelled.")
            return

        if self.selected_project is None or self.selected_task_index is None:
            self.notify("No task selected.", severity="warning")
            return

        updated = update_task(
            self.projects,
            self.selected_project,
            self.selected_task_index,
            task_data["task"],
            task_data["assignee"],
            task_data["start"],
            task_data["end"],
        )

        if not updated:
            self.notify("Could not update task.", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_details()
        self.refresh_gantt_view()
        self.notify(f"Task '{task_data['task'].strip()}' updated.")

    def action_delete_selected(self) -> None:
        task = self.get_selected_task()

        if task and self.selected_project is not None:
            self.push_screen(
                ConfirmScreen(
                    "Delete Task",
                    f"Delete task '{task['task']}' from '{self.selected_project}'?",
                ),
                self.handle_delete_task,
            )
            return

        if self.selected_project:
            self.push_screen(
                ConfirmScreen(
                    "Delete Project",
                    f"Delete project '{self.selected_project}'?",
                ),
                self.handle_delete_project,
            )
            return

        self.notify("Select a project or task first.", severity="warning")

    def handle_delete_task(self, confirmed: bool) -> None:
        if not confirmed:
            self.notify("Deletion cancelled.")
            return

        if self.selected_project is None or self.selected_task_index is None:
            self.notify("No valid task selected.", severity="warning")
            return

        tasks = self.projects.get(self.selected_project, [])
        if not (0 <= self.selected_task_index < len(tasks)):
            self.notify("No valid task selected.", severity="warning")
            return

        task_name = tasks[self.selected_task_index]["task"]
        removed = delete_task(self.projects, self.selected_project, self.selected_task_index)

        if not removed:
            self.notify("Could not delete task.", severity="warning")
            return

        if self.selected_project not in self.projects:
            removed_project_name = self.selected_project
            self.selected_project = None
            self.selected_task_index = None
            save_projects(self.projects)
            self.refresh_project_tree()
            self.refresh_details()
            self.refresh_gantt_view()
            self.notify(
                f"Task '{task_name}' deleted. Project '{removed_project_name}' removed because it became empty."
            )
            return

        self.selected_task_index = None
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_details()
        self.refresh_gantt_view()
        self.notify(f"Task '{task_name}' deleted.")

    def handle_delete_project(self, confirmed: bool) -> None:
        if not confirmed:
            self.notify("Deletion cancelled.")
            return

        project_name = self.selected_project
        if not project_name:
            return

        removed = delete_project(self.projects, project_name)

        if not removed:
            self.notify("Could not delete project.", severity="warning")
            return

        self.selected_project = None
        self.selected_task_index = None
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_details()
        self.refresh_gantt_view()
        self.notify(f"Project '{project_name}' deleted.")

    def action_attach_file(self) -> None:
        task = self.get_selected_task()
        if not task:
            self.notify("Select a task first.", severity="warning")
            return

        self.push_screen(AttachFileScreen(), self.handle_attach_file)

    def handle_attach_file(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("Attachment cancelled.")
            return

        task = self.get_selected_task()
        if not task:
            self.notify("No task selected.", severity="warning")
            return

        attachments = task.setdefault("attachments", [])
        if file_path in attachments:
            self.notify("File already attached.", severity="warning")
            return

        attachments.append(file_path)
        save_projects(self.projects)
        self.refresh_details()
        self.notify("File attached.")

    def action_open_attachment(self) -> None:
        task = self.get_selected_task()
        if not task:
            self.notify("Select a task first.", severity="warning")
            return

        attachments = task.get("attachments", [])
        if not attachments:
            self.notify("This task has no attachments.", severity="warning")
            return

        if len(attachments) == 1:
            self.open_file_path(attachments[0])
            return

        self.push_screen(
            AttachmentPickerScreen("Open Attachment", attachments),
            self.handle_open_attachment_selection,
        )

    def handle_open_attachment_selection(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("Open attachment cancelled.")
            return

        self.open_file_path(file_path)

    def open_file_path(self, file_path: str) -> None:
        if not os.path.exists(file_path):
            self.notify(f"File not found: {file_path}", severity="error")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path], check=False)
            else:
                subprocess.run(["xdg-open", file_path], check=False)

            self.notify(f"Opened: {file_path}")
        except Exception as exc:
            self.notify(f"Could not open file: {exc}", severity="error")

    def action_remove_attachment(self) -> None:
        task = self.get_selected_task()
        if not task:
            self.notify("Select a task first.", severity="warning")
            return

        attachments = task.get("attachments", [])
        if not attachments:
            self.notify("This task has no attachments.", severity="warning")
            return

        if len(attachments) == 1:
            removed = attachments.pop()
            save_projects(self.projects)
            self.refresh_details()
            self.notify(f"Removed attachment: {removed}")
            return

        self.push_screen(
            AttachmentPickerScreen("Remove Attachment", attachments),
            self.handle_remove_attachment_selection,
        )

    def handle_remove_attachment_selection(self, file_path: str | None) -> None:
        if not file_path:
            self.notify("Remove attachment cancelled.")
            return

        task = self.get_selected_task()
        if not task:
            self.notify("No task selected.", severity="warning")
            return

        attachments = task.get("attachments", [])
        if file_path not in attachments:
            self.notify("Attachment no longer exists.", severity="warning")
            return

        attachments.remove(file_path)
        save_projects(self.projects)
        self.refresh_details()
        self.notify(f"Removed attachment: {file_path}")

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
        self.notify(f"Theme changed to {self.theme_name}.")

    def action_toggle_project_selection(self) -> None:
        tree = self.query_one("#projects", Tree)
        node = tree.cursor_node

        if node is None or not isinstance(node.data, dict):
            return

        project_name = node.data.get("project")

        if project_name not in self.projects:
            return

        if project_name in self.selected_projects:
            self.selected_projects.remove(project_name)
            self.notify(f"Removed '{project_name}' from Gantt selection.")
        else:
            self.selected_projects.add(project_name)
            self.notify(f"Added '{project_name}' to Gantt selection.")

        self.refresh_project_tree()
        self.refresh_gantt_view()

    def _shift_month(self, date_value: date, offset: int) -> date:
        target_year = date_value.year + (date_value.month - 1 + offset) // 12
        target_month = (date_value.month - 1 + offset) % 12 + 1
        target_day = min(date_value.day, monthrange(target_year, target_month)[1])
        return date_value.replace(year=target_year, month=target_month, day=target_day)

    def _month_bounds(self, date_value: date) -> tuple[date, date]:
        first_day = date_value.replace(day=1)
        last_day = date_value.replace(day=monthrange(date_value.year, date_value.month)[1])
        return first_day, last_day

    def get_base_gantt_range(self) -> tuple[date, date]:
        today = datetime.now().date()
        selected_rows = []
        selected = self.get_selected_projects_for_gantt()

        for project_name in selected:
            for task in self.projects.get(project_name, []):
                selected_rows.append(task)

        if not selected_rows:
            return self._month_bounds(today)

        start = min(task["start"].date() for task in selected_rows)
        end = max(task["end"].date() for task in selected_rows)

        buffer_days = 3
        start -= timedelta(days=buffer_days)
        end += timedelta(days=buffer_days)

        return start, end

    def get_gantt_visible_range(self) -> tuple[date, date]:
        start, end = self.get_base_gantt_range()

        if self.gantt_day_offset == 0:
            return start, end

        shift = timedelta(days=self.gantt_day_offset)
        return start + shift, end + shift


def main() -> None:
    PyGanttApp().run()


if __name__ == "__main__":
    main()

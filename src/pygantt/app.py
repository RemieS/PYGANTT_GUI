from datetime import datetime, timedelta
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
        "task_bar": "#ff00d4",
        "task_bar_today": "#00f0ff",
        "weekend_fill": "#444444",
        "text": "white",
        "background": "#000000",
    },
    "ice_neon": {
        "banner": "#6fffe9",
        "border_primary": "#6fffe9",
        "border_secondary": "#9b5de5",
        "border_task": "#00bbf9",
        "task_bar": "#00bbf9",
        "task_bar_today": "#9b5de5",
        "weekend_fill": "#3a3a3a",
        "text": "white",
        "background": "#000000",
    },
    "acid_neon": {
        "banner": "#39ff14",
        "border_primary": "#39ff14",
        "border_secondary": "#ffea00",
        "border_task": "#39ff14",
        "task_bar": "#39ff14",
        "task_bar_today": "#ffea00",
        "weekend_fill": "#444444",
        "text": "white",
        "background": "#000000",
    },
    "bw_night": {
        "banner": "white",
        "border_primary": "white",
        "border_secondary": "white",
        "border_task": "white",
        "task_bar": "white",
        "task_bar_today": "white",
        "weekend_fill": "#666666",
        "text": "white",
        "background": "#000000",
    },
    "bw_day": {
        "banner": "black",
        "border_primary": "black",
        "border_secondary": "black",
        "border_task": "black",
        "task_bar": "black",
        "task_bar_today": "black",
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
        theme = self.app.theme_data

        self.update(
            f"[bold underline {theme['banner']}]{banner}[/]\n"
            f"[italic {theme['text']}]{subtitle}[/]"
        )


class TaskDetails(Static):
    def show_task(self, task: dict | None) -> None:
        if not task:
            self.update("No task selected.")
            return

        self.update(
            f"[b]{task['task']}[/b]\n"
            f"Assignee: {task['assignee']}\n"
            f"Start: {task['start'].strftime('%Y-%m-%d')}\n"
            f"End: {task['end'].strftime('%Y-%m-%d')}"
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

        project_name = self.query_one("#project_name_input", Input).value
        self.dismiss(project_name if project_name.strip() else None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        project_name = event.value
        self.dismiss(project_name if project_name.strip() else None)


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
        task_name = self.query_one("#task_name_input", Input).value
        assignee = self.query_one("#assignee_input", Input).value
        start_raw = self.query_one("#start_input", Input).value.strip()
        end_raw = self.query_one("#end_input", Input).value.strip()

        if not task_name.strip() or not assignee.strip():
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
        width: 32;
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
        width: 32;
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
        ("[", "previous_gantt_month", "Prev Month"),
        ("]", "next_gantt_month", "Next Month"),
        ("0", "reset_gantt_month", "Current Month"),
        ("p", "cycle_theme", "Theme"),
    ]

    def __init__(self):
        super().__init__()
        self.projects = load_projects()
        self.selected_project: str | None = None
        self.selected_task_index: int | None = None
        self.selected_projects: set[str] = set()
        self.gantt_month_offset = 0

        self.theme_names = list(THEMES.keys())
        self.theme_name = "retro_neon"
        self.theme_data = THEMES[self.theme_name]

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
        theme = self.theme_data

        self.styles.background = theme["background"]

        self.query_one("#banner").styles.border = ("round", theme["border_primary"])
        self.query_one("#banner").styles.background = theme["background"]
        self.query_one("#banner").styles.color = theme["text"]

        self.query_one("#projects").styles.border = ("solid", theme["border_primary"])
        self.query_one("#projects").styles.background = theme["background"]
        self.query_one("#projects").styles.color = theme["text"]

        self.query_one("#details").styles.border = ("solid", theme["border_secondary"])
        self.query_one("#details").styles.background = theme["background"]
        self.query_one("#details").styles.color = theme["text"]

        self.query_one("#gantt-labels-scroll").styles.border = ("solid", theme["border_primary"])
        self.query_one("#gantt-labels-scroll").styles.background = theme["background"]
        self.query_one("#gantt-labels-scroll").styles.color = theme["text"]

        self.query_one("#gantt-timeline-scroll").styles.border = ("solid", theme["border_primary"])
        self.query_one("#gantt-timeline-scroll").styles.background = theme["background"]
        self.query_one("#gantt-timeline-scroll").styles.color = theme["text"]

        self.query_one("#gantt-labels").styles.background = theme["background"]
        self.query_one("#gantt-labels").styles.color = theme["text"]

        self.query_one("#gantt-timeline").styles.background = theme["background"]
        self.query_one("#gantt-timeline").styles.color = theme["text"]

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

    def get_selected_projects_for_gantt(self) -> list[str]:
        return (
            sorted(self.selected_projects)
            if self.selected_projects
            else ([self.selected_project] if self.selected_project else [])
        )

    def refresh_gantt_view(self) -> None:
        labels = self.query_one("#gantt-labels", Static)
        timeline = self.query_one("#gantt-timeline", Static)

        selected = self.get_selected_projects_for_gantt()
        start_date, end_date = self.get_gantt_visible_range()

        left_lines, right_lines = self.build_gantt_lines(
            selected,
            self.projects,
            start_date,
            end_date,
            2,
        )

        labels.update("\n".join(left_lines))
        timeline.update("\n".join(right_lines))

    def build_gantt_lines(
        self,
        selected_projects: list[str],
        projects: dict[str, list[dict]],
        start_date,
        end_date,
            _cell_width: int,  # ignore incoming value
    ) -> tuple[list[str], list[str]]:

        today = datetime.now().date()

        total_days = (end_date - start_date).days + 1
        days = [start_date + timedelta(days=i) for i in range(total_days)]

        # 👉 DYNAMIC WIDTH BASED ON SCREEN
        scroll = self.query_one("#gantt-timeline-scroll", ScrollableContainer)
        available_width = max(20, scroll.size.width - 4)

        # compute width per column
        cell_width = max(2, min(6, available_width // total_days - 1))

        rows = []
        for project_name in selected_projects:
            for task in projects.get(project_name, []):
                rows.append(
                    {
                        "project": project_name,
                        "task": task["task"],
                        "assignee": task["assignee"],
                        "start": task["start"].date(),
                        "end": task["end"].date(),
                    }
                )

        row_labels = [f"{row['project']} / {row['task']}" for row in rows]

        left_lines = []
        right_lines = []
        theme = self.theme_data

        def fit(value: str) -> str:
            value = value[:cell_width]
            return f"{value:^{cell_width}}"

        def grouped(values):
            prev = None
            cells = []
            for v in values:
                shown = v if v != prev else ""
                cells.append(fit(shown))
                prev = v
            return "│".join(cells)

        def plain(values):
            return "│".join(fit(v) for v in values)

        def bar(style):
            return f"[{style}]{'█' * cell_width}[/]"

        def empty():
            return " " * cell_width

        def separator():
            return "│".join(empty() for _ in days)

        # HEADER
        year = [f"{d.year % 100:02d}" for d in days]
        month = [f"{d.month:02d}" for d in days]
        week = [f"{d.isocalendar().week:02d}" for d in days]
        date = [f"{d.day:02d}" for d in days]
        dow = [d.strftime("%a")[:2] for d in days]

        left_lines += ["Yr", "Mo", "Wk", "Dt", "Dy"]
        right_lines += [
            grouped(year),
            grouped(month),
            grouped(week),
            plain(date),
            plain(dow),
        ]

        left_lines.append("─" * 24)
        right_lines.append("─" * ((cell_width + 1) * total_days - 1))

        if not rows:
            left_lines.append("No tasks planned")
            row = []
            for d in days:
                if d == today:
                    row.append(bar(f"bold {theme['task_bar_today']}"))
                elif d.weekday() >= 5:
                    row.append(fit("░" * cell_width))
                else:
                    row.append(fit(""))
            right_lines.append("│".join(row))
            return left_lines, right_lines

        # TASK ROWS
        for i, (row, label) in enumerate(zip(rows, row_labels)):
            left_lines.append(label)
            cells = []

            for d in days:
                in_task = row["start"] <= d <= row["end"]
                is_today = d == today
                weekend = d.weekday() >= 5

                if in_task and is_today:
                    cells.append(bar(f"bold {theme['task_bar_today']}"))
                elif in_task:
                    cells.append(bar(f"bold {theme['task_bar']}"))
                elif is_today:
                    cells.append(bar(f"bold {theme['task_bar_today']}"))
                elif weekend:
                    cells.append(fit("░" * cell_width))
                else:
                    cells.append(empty())

            right_lines.append("│".join(cells))

            # separator row
            if i < len(rows) - 1:
                left_lines.append("")
                right_lines.append(separator())

        return left_lines, right_lines

    def get_selected_task(self) -> dict | None:
        if self.selected_project is None or self.selected_task_index is None:
            return None

        tasks = self.projects.get(self.selected_project, [])
        if 0 <= self.selected_task_index < len(tasks):
            return tasks[self.selected_task_index]
        return None

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

    def action_previous_gantt_month(self) -> None:
        self.gantt_month_offset -= 1
        self.refresh_gantt_view()

    def action_next_gantt_month(self) -> None:
        self.gantt_month_offset += 1
        self.refresh_gantt_view()

    def action_reset_gantt_month(self) -> None:
        self.gantt_month_offset = 0
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

        data = node.data
        project_name = data.get("project")

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
                    f"Delete task '{task['task']}' from '{self.selected_project}'?"
                ),
                self.handle_delete_task,
            )
            return

        if self.selected_project:
            self.push_screen(
                ConfirmScreen(
                    "Delete Project",
                    f"Delete project '{self.selected_project}'?"
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

    def _shift_month(self, date_value, offset: int):
        year = date_value.year + (date_value.month - 1 + offset) // 12
        month = (date_value.month - 1 + offset) % 12 + 1
        return date_value.replace(year=year, month=month, day=1)

    def _month_bounds(self, date_value):
        first_day = date_value.replace(day=1)
        last_day = date_value.replace(day=monthrange(date_value.year, date_value.month)[1])
        return first_day, last_day

    def get_gantt_visible_range(self):
        today = datetime.now().date()

        selected_rows = []
        selected = self.get_selected_projects_for_gantt()

        for project_name in selected:
            for task in self.projects.get(project_name, []):
                selected_rows.append(task)

        if selected_rows:
            anchor = min(task["start"].date() for task in selected_rows)
        else:
            anchor = today

        visible_month = self._shift_month(anchor, self.gantt_month_offset)
        return self._month_bounds(visible_month)


def main() -> None:
    PyGanttApp().run()


if __name__ == "__main__":
    main()

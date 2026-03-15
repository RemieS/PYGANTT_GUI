from datetime import datetime, timedelta


from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import (
    Header,
    Footer,
    Tree,
    DataTable,
    Static,
    Input,
    Button,
    Label,
    TabbedContent,
    TabPane,
)

from data import (
    load_projects,
    save_projects,
    add_project,
    add_task,
    update_task,
    delete_project,
    delete_task,
)

class Banner(Static):
    def on_mount(self) -> None:
        banner = r"""
██████╗ ██╗   ██╗ ██████╗  █████╗ ███╗   ██╗████████╗████████╗
██╔══██╗╚██╗ ██╔╝██╔════╝ ██╔══██╗████╗  ██║╚══██╔══╝╚══██╔══╝
██████╔╝ ╚████╔╝ ██║  ███╗███████║██╔██╗ ██║   ██║      ██║
██╔═══╝   ╚██╔╝  ██║   ██║██╔══██║██║╚██╗██║   ██║      ██║
██║        ██║   ╚██████╔╝██║  ██║██║ ╚████║   ██║      ██║
╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝      ╚═╝
"""
        subtitle = "A Python-based retro Gantt chart tool, by Remie Stronks"

        self.update(
            f"[bold underline #ff3df5]{banner}[/]\n"
            # f"[bold #ff3df5]{banner}[/]\n"
            f"[italic white]{subtitle}[/]"
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


from datetime import datetime, timedelta
from textual.widgets import Static
import calendar


class GanttView(Static):
    CELL_WIDTH = 3
    GLOSSARY_WIDTH = 6

    def _cell(self, text: str, *, weekend: bool = False, style: str = "") -> str:
        text = str(text)
        text = f"{text:^{self.CELL_WIDTH}}"[:self.CELL_WIDTH]

        styles = []
        if weekend:
            styles.append("dim")
        if style:
            styles.append(style)

        if styles:
            return f"[{' '.join(styles)}]{text}[/]"
        return text

    def _left_prefix(self, glossary: str, row_label: str, row_label_width: int) -> str:
        return f"{glossary:<{self.GLOSSARY_WIDTH}} {row_label:<{row_label_width}} │"

    def _separator_row(self, row_label_width: int, total_days: int) -> str:
        return (
            " " * self.GLOSSARY_WIDTH
            + " "
            + "─" * row_label_width
            + "─┼"
            + "┼".join("─" * self.CELL_WIDTH for _ in range(total_days))
            + "┼"
        )

    def _month_bounds(self, date_value):
        first_day = date_value.replace(day=1)
        last_day_num = calendar.monthrange(date_value.year, date_value.month)[1]
        last_day = date_value.replace(day=last_day_num)
        return first_day, last_day

    def _grouped_row(
        self,
        label: str,
        values: list[str],
        days: list,
        today,
        row_label_width: int,
    ) -> str:
        row = self._left_prefix(label, "", row_label_width)
        previous = None

        for value, day in zip(values, days):
            weekend = day.weekday() >= 5
            is_today = day == today
            style = "reverse" if is_today else ""

            shown = value if value != previous else ""
            row += self._cell(shown, weekend=weekend, style=style) + "│"
            previous = value

        return row

    def _plain_row(
        self,
        label: str,
        values: list[str],
        days: list,
        today,
        row_label_width: int,
    ) -> str:
        row = self._left_prefix(label, "", row_label_width)

        for value, day in zip(values, days):
            weekend = day.weekday() >= 5
            is_today = day == today
            style = "reverse" if is_today else ""
            row += self._cell(value, weekend=weekend, style=style) + "│"

        return row

    def show_tasks(
        self,
        selected_projects: list[str],
        projects: dict[str, list[dict]],
        start_date,
        end_date,
    ) -> None:
        
        if not selected_projects:
            self.update("No project selected.")
            return

        rows: list[dict] = []
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

        today = datetime.now().date()

        total_days = (end_date - start_date).days + 1
        days = [start_date + timedelta(days=i) for i in range(total_days)]

        if rows:
            row_labels = [f"{row['project']} / {row['task']}" for row in rows]
            row_label_width = max(24, max(len(label) for label in row_labels))
        else:
            row_labels = []
            row_label_width = 24

        year_values = [f"{day.year % 100:02d}" for day in days]
        month_values = [day.strftime("%b") for day in days]
        week_values = [f"W{day.isocalendar().week:02d}" for day in days]
        date_values = [f"{day.day:02d}" for day in days]
        day_values = [day.strftime("%a")[:2] for day in days]

        separator = self._separator_row(row_label_width, total_days)

        month_title = start_date.strftime("%B %Y")

        lines = [
            f"[b]Projects:[/b] {', '.join(selected_projects) if selected_projects else 'None'}",
            f"[b]Visible month:[/b] {month_title}",
            "",
            self._grouped_row("Year", year_values, days, today, row_label_width),
            self._grouped_row("Month", month_values, days, today, row_label_width),
            self._grouped_row("Week", week_values, days, today, row_label_width),
            self._plain_row("Date", date_values, days, today, row_label_width),
            self._plain_row("Day", day_values, days, today, row_label_width),
            separator,
        ]

        if not rows:
            gantt_row = self._left_prefix("", "No tasks planned", row_label_width)

            for day in days:
                weekend = day.weekday() >= 5
                is_today = day == today

                if weekend and is_today:
                    cell = self._cell("░", style="reverse dim")
                elif weekend:
                    cell = self._cell("░", weekend=True)
                elif is_today:
                    cell = self._cell(" ", style="reverse")
                else:
                    cell = self._cell(" ")

                gantt_row += cell + "│"

            lines.append(gantt_row)
            lines.append(separator)

        else:
            for row, label in zip(rows, row_labels):
                gantt_row = self._left_prefix("", label, row_label_width)

                for day in days:
                    weekend = day.weekday() >= 5
                    in_task = row["start"] <= day <= row["end"]
                    is_today = day == today

                    if in_task and weekend and is_today:
                        cell = self._cell("█", style="reverse dim")
                    elif in_task and is_today:
                        cell = self._cell("█", style="reverse bold green")
                    elif in_task and weekend:
                        cell = self._cell("█", weekend=True)
                    elif in_task:
                        cell = self._cell("█", style="bold green")
                    elif weekend and is_today:
                        cell = self._cell("░", style="reverse dim")
                    elif weekend:
                        cell = self._cell("░", weekend=True)
                    elif is_today:
                        cell = self._cell(" ", style="reverse")
                    else:
                        cell = self._cell(" ")

                    gantt_row += cell + "│"

                lines.append(gantt_row)
                lines.append(separator)

        lines.append("")
        lines.append("[dim]Full months are shown. Grouped headers reduce repetition. Weekends are dimmed.[/dim]")

        self.update("\n".join(lines))

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
        self.selected_projects: set[str] = set()
        self.multi_select_mode = True
        self.gantt_month_offset = 0

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
    
    #banner-scroll {
        height: 10;
        overflow-x: auto;
        overflow-y: auto;
        border: round yellow;
    }
    #banner {
        height: auto;
        padding: 1 2;
        border: round cyan;
        color: white;
    }

    #main {
        height: 1fr;
    }

    #projects {
        width: 30%;
        border: solid cyan;
    }

    #right-pane {
        width: 70%;
    }

    #tabs {
        height: 1fr;
    }

    #tasks-pane {
        height: 1fr;
    }

    #tasks {
        height: 70%;
        border: solid green;
    }

    #details {
        height: 30%;
        border: solid magenta;
        padding: 1;
    }

    #gantt-scroll {
        overflow-x: auto;
        overflow-y: auto;
        border: solid cyan;
    }

    #gantt {
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
        ("g", "show_gantt", "Gantt"),
        ("w", "show_tasks", "Tasks"),
        ("space", "toggle_project_selection", "Toggle Project"),
        ("[", "previous_gantt_month", "Prev Month"),
        ("]", "next_gantt_month", "Next Month"),
        ("0", "reset_gantt_month", "Current Month"),
    ]

    def __init__(self):
        super().__init__()
        self.projects = load_projects()
        self.selected_project: str | None = None
        self.selected_projects: set[str] = set()
        self.gantt_month_offset = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Banner(id="banner")

        with Horizontal(id="main"):
            yield Tree("Projects", id="projects")

            with Vertical(id="right-pane"):
                with TabbedContent(id="tabs"):
                    with TabPane("Tasks", id="tasks-tab"):
                        with Vertical(id="tasks-pane"):
                            yield DataTable(id="tasks")
                            yield TaskDetails("No task selected.", id="details")

                    with TabPane("Gantt", id="gantt-tab"):
                        with ScrollableContainer(id="gantt-scroll"):
                            yield GanttView("No project selected.", id="gantt")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#tasks", DataTable)
        table.cursor_type = "row"
        table.add_columns("Task", "Assignee", "Start", "End")
        self.refresh_project_tree()
        self.refresh_gantt_view()

    def refresh_project_tree(self) -> None:
        tree = self.query_one("#projects", Tree)
        tree.clear()
        root = tree.root

        for project_name in self.projects:
            label = f"✔ {project_name}" if project_name in self.selected_projects else project_name
            root.add(label, data=project_name)

        root.expand()

    def action_toggle_project_selection(self) -> None:
        tree = self.query_one("#projects", Tree)
        node = tree.cursor_node
        if node is None:
            return

        project_name = str(node.label)
        if project_name not in self.projects:
            return

        if project_name in self.selected_projects:
            self.selected_projects.remove(project_name)
            self.notify(f"Removed '{project_name}' from Gantt selection.")
        else:
            self.selected_projects.add(project_name)
            self.notify(f"Added '{project_name}' to Gantt selection.")

        self.refresh_gantt_view()    

    def refresh_task_table(self) -> None:
        table = self.query_one("#tasks", DataTable)
        table.clear()

        if not self.selected_project or self.selected_project not in self.projects:
            self.query_one("#details", TaskDetails).show_task(None)
            self.refresh_gantt_view()
            return

        for task in self.projects[self.selected_project]:
            table.add_row(
                task["task"],
                task["assignee"],
                task["start"].strftime("%Y-%m-%d"),
                task["end"].strftime("%Y-%m-%d"),
            )

        self.query_one("#details", TaskDetails).show_task(None)
        self.refresh_gantt_view()

    def refresh_gantt_view(self) -> None:
        gantt = self.query_one("#gantt", GanttView)

        selected = sorted(self.selected_projects) if self.selected_projects else (
            [self.selected_project] if self.selected_project else []
        )

        start_date, end_date = self.get_gantt_visible_range()
        gantt.show_tasks(selected, self.projects, start_date, end_date)

    def get_current_task_index(self) -> int | None:
        if not self.selected_project or self.selected_project not in self.projects:
            return None

        table = self.query_one("#tasks", DataTable)
        row_index = table.cursor_row
        tasks = self.projects[self.selected_project]

        if 0 <= row_index < len(tasks):
            return row_index

        return None

    def get_current_task(self) -> dict | None:
        row_index = self.get_current_task_index()

        if row_index is None or not self.selected_project:
            return None

        return self.projects[self.selected_project][row_index]

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        project_name = event.node.data or str(event.node.label)

        if project_name not in self.projects:
            return

        self.selected_project = project_name
        self.refresh_task_table()
        self.refresh_gantt_view()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        task = self.get_current_task()
        self.query_one("#details", TaskDetails).show_task(task)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_edit_selected()

    def action_show_gantt(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "gantt-tab"

    def action_show_tasks(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "tasks-tab"

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
        if not task_data:
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
        self.refresh_task_table()
        self.notify(f"Task '{task_data['task'].strip()}' added to '{self.selected_project}'.")

    def action_edit_selected(self) -> None:
        if not self.selected_project:
            self.notify("Select a project first.", severity="warning")
            return

        row_index = self.get_current_task_index()
        if row_index is None:
            self.notify("Select a task to edit.", severity="warning")
            return

        task = self.projects[self.selected_project][row_index]

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

        if not self.selected_project:
            self.notify("No project selected.", severity="warning")
            return

        row_index = self.get_current_task_index()
        if row_index is None:
            self.notify("No task selected.", severity="warning")
            return

        updated = update_task(
            self.projects,
            self.selected_project,
            row_index,
            task_data["task"],
            task_data["assignee"],
            task_data["start"],
            task_data["end"],
        )

        if not updated:
            self.notify("Could not update task.", severity="warning")
            return

        save_projects(self.projects)
        self.refresh_task_table()
        self.query_one("#details", TaskDetails).show_task(None)
        self.notify(f"Task '{task_data['task'].strip()}' updated.")

    def action_delete_selected(self) -> None:
        if self.selected_project:
            row_index = self.get_current_task_index()
            tasks = self.projects.get(self.selected_project, [])

            if row_index is not None and 0 <= row_index < len(tasks):
                task_name = tasks[row_index]["task"]
                self.push_screen(
                    ConfirmScreen(
                        "Delete Task",
                        f"Delete task '{task_name}' from '{self.selected_project}'?"
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

        if not self.selected_project:
            return

        row_index = self.get_current_task_index()
        tasks = self.projects.get(self.selected_project, [])

        if row_index is None or not (0 <= row_index < len(tasks)):
            self.notify("No valid task selected.", severity="warning")
            return

        task_name = tasks[row_index]["task"]
        removed = delete_task(self.projects, self.selected_project, row_index)

        if not removed:
            self.notify("Could not delete task.", severity="warning")
            return

        if self.selected_project not in self.projects:
            removed_project_name = self.selected_project
            self.selected_project = None
            save_projects(self.projects)
            self.refresh_project_tree()
            self.refresh_task_table()
            self.notify(
                f"Task '{task_name}' deleted. Project '{removed_project_name}' removed because it became empty."
            )
            return

        save_projects(self.projects)
        self.refresh_task_table()
        self.query_one("#details", TaskDetails).show_task(None)
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
        save_projects(self.projects)
        self.refresh_project_tree()
        self.refresh_task_table()
        self.notify(f"Project '{project_name}' deleted.")

    def _shift_month(self, date_value, offset: int):
        year = date_value.year + (date_value.month - 1 + offset) // 12
        month = (date_value.month - 1 + offset) % 12 + 1
        return date_value.replace(year=year, month=month, day=1)

    def _month_bounds(self, date_value):
        from calendar import monthrange

        first_day = date_value.replace(day=1)
        last_day = date_value.replace(day=monthrange(date_value.year, date_value.month)[1])
        return first_day, last_day

    def get_gantt_visible_range(self):
        today = datetime.now().date()

        selected_rows = []
        selected = sorted(self.selected_projects) if self.selected_projects else (
            [self.selected_project] if self.selected_project else []
        )

        for project_name in selected:
            for task in self.projects.get(project_name, []):
                selected_rows.append(task)

        if selected_rows:
            anchor = min(task["start"].date() for task in selected_rows)
        else:
            anchor = today

        month_offset = getattr(self, "gantt_month_offset", 0)
        visible_month = self._shift_month(anchor, self.gantt_month_offset)
        return self._month_bounds(visible_month)

    def action_toggle_project_selection(self) -> None:
        tree = self.query_one("#projects", Tree)
        node = tree.cursor_node

        if node is None:
            return

        project_name = node.data or str(node.label)

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


if __name__ == "__main__":
    PyGanttApp().run()
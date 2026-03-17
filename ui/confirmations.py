from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm


def render_confirmation(
    console: Console,
    action: str,
    details: dict,
) -> bool:
    details_grid = Table.grid(padding=(0, 2))
    details_grid.add_column(style="bold")
    details_grid.add_column()

    details_grid.add_row("Action", action)
    for key, value in details.items():
        display_value = str(value)
        if key != "body" and len(display_value) > 100:
            display_value = display_value[:100] + "..."
        details_grid.add_row(key.capitalize(), display_value)

    console.print(Panel(
        details_grid,
        title="[bold yellow]⚠️  CONFIRMATION REQUISE[/]",
        border_style="yellow",
        padding=(1, 2),
    ))

    return Confirm.ask("[bold]Confirmer cette action ?[/]", console=console)

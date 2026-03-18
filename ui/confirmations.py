from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm

from ui.themes import C, BORDERS, BOX


def render_confirmation(
    console: Console,
    action: str,
    details: dict,
) -> bool:
    details_grid = Table.grid(padding=(0, 2))
    details_grid.add_column(style=f"bold {C['text_dim']}")
    details_grid.add_column()

    details_grid.add_row("Action", f"[{C['amber']}]{action}[/]")
    for key, value in details.items():
        display_value = str(value)
        if key != "body" and len(display_value) > 100:
            display_value = display_value[:100] + "..."
        details_grid.add_row(key.capitalize(), f"[{C['text']}]{display_value}[/]")

    console.print(Panel(
        details_grid,
        title=f"[bold {C['amber']}]⚠️  CONFIRMATION REQUISE[/]",
        title_align="left",
        border_style=BORDERS["confirm"],
        box=BOX,
        padding=(1, 2),
    ))

    return Confirm.ask(f"[bold {C['text']}]Confirmer cette action ?[/]", console=console)

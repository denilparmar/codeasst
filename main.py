from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from observability import get_logger

load_dotenv()

console = Console()
logger = get_logger(__name__)

COMMANDS = {
    "/index <path>": "Index a codebase",
    "/ask <question>": "Ask a question about the indexed code",
    "/help": "Show available commands",
    "/exit, /quit": "Quit CodeAsst",
}


def show_banner() -> None:
    console.print(
        Panel.fit(
            "[bold blue]CodeAsst[/bold blue] — A RAG-powered code assistant\n"
            "[dim]Happy coding![/dim]",
            border_style="blue",
        )
    )


def show_help() -> None:
    table = Table(title="Available Commands", title_justify="left", show_edge=False)
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description")
    for command, description in COMMANDS.items():
        table.add_row(command, description)
    console.print(table)
    console.print()


def handle_index(path: str) -> None:
    if not path:
        console.print("[yellow]Usage: /index <path>[/yellow]")
        return
    logger.info(f"Index command received: {path}")
    console.print(f"[dim]Indexing {path}...[/dim]")


def handle_ask(question: str) -> None:
    if not question:
        console.print("[yellow]Usage: /ask <question>[/yellow]")
        return
    logger.info(f"Ask command received: {question}")
    console.print(f"[dim]Searching for: {question}...[/dim]")


def run() -> None:
    logger.info("Starting codeasst...")
    show_banner()
    show_help()

    while True:
        try:
            user_input = Prompt.ask("[bold green]>[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/exit"
            console.print()

        if not user_input:
            continue

        command, _, args = user_input.partition(" ")
        command = command.lower()
        args = args.strip()

        if command in ("/exit", "/quit"):
            logger.info("Shutting down")
            console.print("[dim]Goodbye![/dim]")
            break
        elif command == "/help":
            show_help()
        elif command == "/index":
            handle_index(args)
        elif command == "/ask":
            handle_ask(args)
        else:
            logger.warning(f"Unknown command received: {user_input}")
            console.print(f"[yellow]Unknown command: {command}[/yellow]\n")
            show_help()


if __name__ == "__main__":
    run()

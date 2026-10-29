from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.table import Table
import chromadb
from config import config
from observability import get_logger
from llm.factory import get_llm, get_embedder
from context.indexers.factory import get_indexer, get_index_inspector
from agent.orchestrator import handle_query
from pathlib import Path
from memory.session import get_current_session, new_session, switch_session
from memory.short_term import get_session_history, get_checkpointer_db_path
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import asyncio
import json
import signal
from agent.factory import build_agent

load_dotenv()

console = Console()
logger = get_logger(__name__)


COMMANDS = {
    "/index <path>": "Index a codebase",
    "/ask <question>": "Ask a question about the indexed code",
    "/show_semantic_index": "Shows all the indexes",
    "/help": "Show available commands",
    "/new_session": "starts a new session",
    "/switch": "switch to a new session",
    "/session": "shows the current session",
    "/session_history [thread_id]": "shows the history for a session (default: current)",
    "/exit, /quit": "Quit CodeAsst",
}


def get_or_create_index():
    repo_path = str(Path.cwd())
    logger.info(f"Checking index for: {repo_path}")
    console.print(f"[dim]Checking index for {repo_path}...[/dim]")
    return get_indexer()(repo_path)


async def initialize(checkpointer):
    """Bootstrap LLM, embedder, and index before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(
        f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]"
    )
    console.print(
        f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]"
    )

    index = get_or_create_index()
    session_id = get_current_session()
    agent = await build_agent(checkpointer)
    console.print(f"[dim]Session: {session_id}[/dim]")

    console.print(f"[green]✓ Ready[/green]\n")
    return llm, embedder, index, agent, session_id


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


def ask_decision(action: dict, allowed: list[str]) -> dict:
    """Show one pending tool call and ask the user what to do with it."""
    console.print(
        Panel(
            f"[bold]{action['name']}[/bold]\n{json.dumps(action['args'], indent=2)}",
            title="[bold yellow]Approval needed[/bold yellow]",
            title_align="left",
            border_style="yellow",
        )
    )
    choice = Prompt.ask("Decision", choices=allowed, default="reject")
    if choice == "approve":
        return {"type": "approve"}
    if choice == "edit":
        raw = Prompt.ask("New args as JSON", default=json.dumps(action["args"]))
        try:
            args = json.loads(raw)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON, rejecting instead.[/red]")
            return {"type": "reject", "message": "User's edit was invalid JSON."}
        return {"type": "edit", "edited_action": {"name": action["name"], "args": args}}
    reason = Prompt.ask("Reason (optional)", default="")
    return {"type": "reject", "message": reason} if reason else {"type": "reject"}


def make_reviewer(status: Status):
    """Build a reviewer that pauses the spinner while asking for approval."""

    async def review(hitl_request: dict) -> list[dict]:
        status.stop()
        allowed = {
            r["action_name"]: r["allowed_decisions"]
            for r in hitl_request["review_configs"]
        }
        try:
            return [
                ask_decision(action, allowed[action["name"]])
                for action in hitl_request["action_requests"]
            ]
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled, rejecting pending tool calls.[/yellow]")
            return [
                {"type": "reject", "message": "User cancelled."}
                for _ in hitl_request["action_requests"]
            ]
        finally:
            status.start()

    return review


async def handle_ask(agent, question: str, thread_id: str) -> None:
    if not question:
        console.print("[yellow]Usage: /ask <question>[/yellow]")
        return
    logger.info(f"Ask command received: {question}")
    with console.status(
        "[dim]Searching the codebase...[/dim]", spinner="dots"
    ) as status:
        response = await handle_query(agent, question, thread_id, make_reviewer(status))

    console.print()
    console.print(
        Panel(
            Markdown(response),
            title=f"[bold cyan]{question}[/bold cyan]",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def show_semantic_index(collection: chromadb.Collection) -> None:
    """Display all documents stored in the ChromaDB collection."""
    results = collection.get(include=["documents", "metadatas", "embeddings"])
    console.print(f"\n[bold]Semantic Index — {collection.count()} chunks[/bold]\n")

    for i, (doc, meta, emb) in enumerate(
        zip(results["documents"], results["metadatas"], results["embeddings"])
    ):
        console.print(
            f"[bold cyan]── Chunk {i+1} ──────────────────────────[/bold cyan]"
        )
        console.print(f"  File     : {meta['source']}")
        console.print(f"  Name     : {meta['name']} ({meta['type']})")
        console.print(f"  Lines    : {meta['start_line']} - {meta['end_line']}")
        console.print(
            f"  Embedding: [{', '.join(f'{v:.4f}' for v in emb[:5])}...] ({len(emb)} dims)"
        )
        console.print(f"  Code     :\n[dim]{doc[:300]}[/dim]\n")


def show_session_history(thread_id: str) -> None:
    history = get_session_history(thread_id=thread_id)
    if not history:
        console.print(f"[dim]No history for session {thread_id}[/dim]\n")
        return
    for message in history:
        style = "cyan" if message["role"] == "user" else "green"
        console.print(
            f"[bold {style}]{message['role']}:[/bold {style}] {message['content']}\n"
        )


async def run() -> None:
    logger.info("Starting codeasst...")
    # asyncio.run() turns Ctrl-C into task cancellation; restore the default
    # handler so Ctrl-C raises KeyboardInterrupt and is handled in cli().
    signal.signal(signal.SIGINT, signal.default_int_handler)
    async with AsyncSqliteSaver.from_conn_string(
        get_checkpointer_db_path()
    ) as checkpointer:
        llm, embedder, index, agent, session_id = await initialize(checkpointer)
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
                await handle_ask(agent, args, session_id)
            elif command == "/show_semantic_index":
                logger.info("Showing semantic index")
                get_index_inspector()(index)
            elif user_input == "/new_session":
                session_id = new_session()
                console.print(f"[green]New session started: {session_id}[/green]")
            elif user_input.startswith("/switch "):
                target = user_input.removeprefix("/switch ").strip()
                session_id = switch_session(target)
                console.print(f"[green]Switched to session: {session_id}[/green]")
            elif command == "/session_history":
                show_session_history(args or session_id)
            elif user_input == "/session":
                console.print(f"[dim]Current session: {session_id}[/dim]")

            else:
                logger.warning(f"Unknown command received: {user_input}")
                console.print(f"[yellow]Unknown command: {command}[/yellow]\n")
                show_help()


def cli() -> None:
    """Console-script entry point."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    cli()

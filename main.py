from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
import chromadb
from config import config
from observability import get_logger
from llm.factory import get_llm, get_embedder
from context.indexers.semantic_chroma import index_codebase
from agent.orchestrator import handle_query
from pathlib import Path

load_dotenv()

console = Console()
logger = get_logger(__name__)


COMMANDS = {
    "/index <path>": "Index a codebase",
    "/ask <question>": "Ask a question about the indexed code",
    "/show_semantic_index": "Shows all the indexes",
    "/help": "Show available commands",
    "/exit, /quit": "Quit CodeAsst",
}


def get_or_create_index() -> chromadb.Collection:
    """Load existing index or create a new one by indexing current directory."""
    chroma_client = chromadb.PersistentClient(path=config["chromadb"]["persist_dir"])
    collection = chroma_client.get_or_create_collection(
        name=config["chromadb"]["collection_name"]
    )

    if collection.count() > 0:
        logger.info(f"Loaded existing index with {collection.count()} chunks")
        console.print(f"[dim]Loaded existing index — {collection.count()} chunks[/dim]")
        return collection

    # Auto-index the current working directory
    repo_path = str(Path.cwd())
    logger.info(f"Indexing repo: {repo_path}")
    console.print(f"[dim]Indexing {repo_path}...[/dim]")
    return index_codebase(repo_path)


def initialize():
    """Bootstrap LLM, embedder, and index before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(
        f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]"
    )
    console.print(
        f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]"
    )

    collection = get_or_create_index()
    console.print(f"[green]✓ Ready — {collection.count()} chunks indexed[/green]\n")
    return llm, embedder, collection


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
    with console.status("[dim]Searching the codebase...[/dim]", spinner="dots"):
        response = handle_query(question)

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


def run() -> None:
    logger.info("Starting codeasst...")
    llm, embedder, collection = initialize()
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
        elif command == "/show_semantic_index":
            show_semantic_index(collection)
        else:
            logger.warning(f"Unknown command received: {user_input}")
            console.print(f"[yellow]Unknown command: {command}[/yellow]\n")
            show_help()


if __name__ == "__main__":
    run()

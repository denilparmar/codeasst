# CodeAsst

CodeAsst is a command-line AI assistant that answers questions about a codebase. Run it from inside any project: it parses and indexes the source code into a vector store, then answers your questions with an LLM agent that searches the index and cites specific files, functions and line numbers. Conversations are saved per project, so you can resume, switch between, and review past sessions.

## Features

- **Code-aware indexing**: uses [tree-sitter](https://tree-sitter.github.io/) to split source files into functions, classes and methods across 16 languages (Python, JavaScript/TypeScript, Java, Go, Rust, C/C++, C#, Ruby, PHP, Swift, Kotlin, Bash). Other files fall back to overlapping line chunks, and docs/config files (`.md`, `.yaml`, `.json`, `.toml`, …) are indexed too. Build and environment folders (`.venv`, `node_modules`, `.git`, `dist`, `build`, …) are skipped.
- **Pluggable vector stores**:
  - **Qdrant** with **hybrid retrieval**: dense embeddings plus BM25 sparse vectors (via FastEmbed). You can set it to dense-only, sparse-only or hybrid.
  - **Qdrant** semantic (dense-only).
  - **ChromaDB**, stored locally on disk.
- **Per-project indexes**: each project gets its own Qdrant collection (`<name>_<folder>_<path hash>`), and an existing index is reused instead of rebuilt.
- **Pluggable LLMs and embeddings**: OpenAI or Anthropic chat models; OpenAI or Hugging Face embeddings.
- **Agentic Q&A**: a LangChain agent calls a `search_codebase` tool before answering, so its answers are based on the actual code.
- **Short-term memory with sessions**: conversation state is saved to SQLite in a `.memory/` folder inside the project you run from (automatically git-ignored). Long conversations are automatically summarized once they exceed a token threshold.
- **Rich terminal UI**: answers are rendered as Markdown in the terminal.

## Directory structure

```
codeasst/
├── main.py                  # CLI entry point: REPL, command handling, startup
├── config.py                # Loads/validates config.yaml; per-project path helpers
├── config.yaml              # LLM, embeddings, vector store, RAG and memory settings
├── pyproject.toml           # Project metadata, dependencies, `codeasst` script
├── agent/
│   ├── factory.py           # Builds the LangChain agent (LLM + tools + memory)
│   ├── orchestrator.py      # Runs a query through the agent for a session
│   └── tools.py             # `search_codebase` tool used by the agent
├── context/
│   ├── indexers/
│   │   ├── code_parser.py       # tree-sitter parsing and file discovery
│   │   ├── factory.py           # Picks the indexer from config
│   │   ├── hybrid_qdrant.py     # Qdrant dense + sparse (BM25) indexing
│   │   ├── semantic_qdrant.py   # Qdrant dense-only indexing
│   │   └── semantic_chroma.py   # ChromaDB indexing
│   └── retrievers/
│       ├── factory.py           # Picks the retriever from config
│       ├── hybrid_qdrant.py
│       ├── semantic_qdrant.py
│       └── semantic_chroma.py
├── llm/
│   └── factory.py           # Chat model and embedder factories
├── memory/
│   ├── session.py           # Create / resume / switch session ids
│   └── short_term.py        # SQLite checkpointer, history, summarization
└── observability/
    └── logger.py            # Logging setup
```

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Qdrant instance (local or Qdrant Cloud), unless you use ChromaDB
- An OpenAI and/or Anthropic API key

### Install

```bash
git clone <repo-url> codeasst
cd codeasst
uv sync
```

This installs CodeAsst in editable mode and provides the `codeasst` command inside the virtual environment. If you add a new top-level package to `pyproject.toml`, run `uv sync --reinstall-package codeasst` to pick it up.

### Configure

Create a `.env` file:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...     # only if llm.provider is anthropic
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...               # only for secured / cloud Qdrant
```

To run Qdrant locally:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Edit `config.yaml` to choose providers:

```yaml
llm:
  provider: openai          # openai | anthropic
  model: gpt-4o

embeddings:
  provider: openai          # openai | huggingface
  model: text-embedding-3-small

vector_store:
  provider: qdrant          # qdrant | chromadb
  retrieval_mode: hybrid    # dense | sparse | hybrid (Qdrant only)

rag:
  mode: hybrid              # semantic | hybrid

memory:
  db_path: .memory/memory.db
  summarize_at_tokens: 4000
  keep_last_messages: 20
```

### Run

CodeAsst indexes the directory you start it from. To use it on another project, `cd` into that project and run the installed command:

```bash
cd /path/to/your/project
/path/to/codeasst/.venv/bin/codeasst
```

To run it on CodeAsst's own repo:

```bash
uv run codeasst
```

The first run on a project builds the index; later runs reuse it.

## Commands

| Command | Description |
| --- | --- |
| `/ask <question>` | Ask a question about the indexed code |
| `/show_semantic_index` | Inspect the chunks stored in the index |
| `/session` | Show the current session id |
| `/new_session` | Start a new conversation session |
| `/switch <session_id>` | Switch to an existing session |
| `/session_history [session_id]` | Show the messages in a session (default: current) |
| `/index <path>` | Index a codebase (not implemented yet; indexing currently happens at startup for the current directory) |
| `/help` | Show available commands |
| `/exit`, `/quit` | Quit CodeAsst |

Example:

```
> /ask where is the vector store chosen?
> /session_history
> /new_session
```

## Data stored in your project

Running CodeAsst in a project creates:

- `.memory/`: session id and SQLite conversation history (git-ignored automatically)
- `.chromadb/`: local index, only when `vector_store.provider` is `chromadb`

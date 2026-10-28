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
- **Terminal tools**: the agent can run shell commands (with a 30-second timeout). See [Agent tools](#agent-tools).
- **MCP servers**: tools from [Model Context Protocol](https://modelcontextprotocol.io/) servers listed in `codeasst_mcp_servers.json` are loaded into the agent at startup. Two servers are configured by default:
  - **Filesystem**: read, write, edit, move and search files, limited to the directory you launch CodeAsst from.
  - **GitHub**: read and change issues, pull requests and files on GitHub.

  See [MCP servers](#mcp-servers).
- **Resilient tool calls**: if a tool raises an error, the agent receives it as the tool's result and can explain or recover, instead of the run failing. Sessions left with an unanswered tool call (for example after a crash) are repaired automatically on the next message.
- **Short-term memory with sessions**: conversation state is saved to SQLite in a `.memory/` folder inside the project you run from (automatically git-ignored). Long conversations are automatically summarized once they exceed a token threshold.
- **Rich terminal UI**: answers are rendered as Markdown in the terminal.

## Directory structure

```
codeasst/
├── main.py                  # CLI entry point: REPL, command handling, startup
├── config.py                # Loads/validates config.yaml; per-project path helpers
├── config.yaml              # LLM, embeddings, vector store, RAG and memory settings
├── pyproject.toml           # Project metadata, dependencies, `codeasst` script
├── codeasst_mcp_servers.json # MCP servers to connect to at startup
├── agent/
│   ├── factory.py           # Builds the LangChain agent (LLM + tools + memory)
│   ├── middleware.py        # Turns tool errors into results; repairs broken sessions
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
├── codeasst_mcp/
│   ├── codeasst_mcp_config.py   # Loads codeasst_mcp_servers.json, resolves ${VAR}s
│   └── codeasst_mcp_client.py   # Connects to the servers and loads their tools
├── llm/
│   └── factory.py           # Chat model and embedder factories
├── memory/
│   ├── session.py           # Create / resume / switch session ids
│   └── short_term.py        # SQLite checkpointer, history, summarization
├── observability/
│   └── logger.py            # Logging setup
└── tools/
    └── terminal_tools.py    # Run shell commands, optionally in a given directory
```

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Qdrant instance (local or Qdrant Cloud), unless you use ChromaDB
- An OpenAI and/or Anthropic API key
- [Node.js](https://nodejs.org/) (for `npx`), to run the filesystem and GitHub MCP servers
- A GitHub [personal access token](https://github.com/settings/personal-access-tokens), for the GitHub MCP server

### Install

```bash
git clone <repo-url> codeasst
cd codeasst
uv sync
```

This installs CodeAsst in editable mode and provides the `codeasst` command inside the virtual environment. If you add a new top-level package to `pyproject.toml`, run `uv sync --reinstall-package codeasst` to pick it up.

To put `codeasst` on your `PATH` instead, install it as a uv tool:

```bash
uv tool install --editable .
```

Code changes in existing packages take effect immediately. After adding or renaming a top-level package (for example `tools/`), or changing the `codeasst` entry point in `pyproject.toml`, reinstall with `uv tool install --editable . --force`. Otherwise you'll get `ModuleNotFoundError` on startup, or the command will run old code.

Keep the install editable: `codeasst_mcp_servers.json` is read from the repo root and isn't packaged.

### Configure

Create a `.env` file:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...     # only if llm.provider is anthropic
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...               # only for secured / cloud Qdrant
GITHUB_TOKEN=github_pat_...      # used by the GitHub MCP server
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

The first run on a project builds the index; later runs reuse it. On every start, CodeAsst also starts and connects to the configured MCP servers.

Press Ctrl-C at any time to quit, including while the agent is answering. If you interrupt a run mid-tool-call, the session is repaired on your next message.

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

## Agent tools

The agent chooses which tools to call while answering a question. It has three built-in tools, plus the tools from each [MCP server](#mcp-servers).

| Tool | Module | Description |
| --- | --- | --- |
| `search_codebase(query)` | `agent/tools.py` | Search the vector index and return the top 5 matching chunks with file, line range and symbol name |
| `run_command(command)` | `tools/terminal_tools.py` | Run a shell command from the current directory |
| `run_in_directory(command, directory)` | `tools/terminal_tools.py` | Run a shell command in the given directory |

Shell commands time out after 30 seconds and return stdout, stderr and a non-zero exit code. Errors are returned as text (for example `Error: command timed out after 30 seconds`) so the agent can recover instead of crashing.

Built-in tools are registered in `build_agent()` in `agent/factory.py`. To add one, define a function decorated with `@tool` from `langchain.tools`, give it a clear docstring (the agent uses it to decide when to call the tool), and add it to the `tools` list. Don't reuse the name of an MCP tool.

> **Warning:** the terminal tools run without asking for confirmation and aren't limited to the project directory. Through them, the agent can run any shell command, including ones that change or delete files outside the project. The command blocklist only catches a few patterns (such as `rm -rf /` and `mkfs`) and is easy to bypass. Use CodeAsst on projects under version control, and don't run it with elevated privileges.

### Filesystem tools (MCP)

The filesystem MCP server ([`@modelcontextprotocol/server-filesystem`](https://www.npmjs.com/package/@modelcontextprotocol/server-filesystem)) adds these tools. They can only access paths inside the directory you launched CodeAsst from (`${CWD}`).

- **Read**: `read_text_file`, `read_media_file`, `read_multiple_files`, `read_file` (deprecated alias of `read_text_file`), `list_directory`, `list_directory_with_sizes`, `directory_tree`, `search_files`, `get_file_info`, `list_allowed_directories`
- **Write**: `write_file`, `edit_file` (line-based edits, with a dry-run option that returns a diff), `create_directory`, `move_file`

The server has no delete tool. To delete a file, the agent has to fall back to `run_command`.

### GitHub tools (MCP)

The GitHub MCP server adds these tools:

- **Read**: `get_file_contents`, `search_code`, `search_repositories`, `search_issues`, `search_users`, `list_commits`, `list_issues`, `get_issue`, `list_pull_requests`, `get_pull_request`, `get_pull_request_files`, `get_pull_request_status`, `get_pull_request_comments`, `get_pull_request_reviews`
- **Write**: `create_or_update_file`, `push_files`, `create_branch`, `create_repository`, `fork_repository`, `create_issue`, `update_issue`, `add_issue_comment`, `create_pull_request`, `create_pull_request_review`, `merge_pull_request`, `update_pull_request_branch`

Example questions:

```
> /ask why was memory/short_term.py changed in the last few commits?
> /ask summarize the open issues on denilparmar/codeasst
> /ask what files does PR #1 change, and how do they affect the agent?
```

> **Warning:** GitHub write tools run immediately, with no confirmation, using your token. Give `GITHUB_TOKEN` only the repositories and permissions you need. Use a fine-grained, read-only token if you only want the agent to read from GitHub.

### Error handling

`ToolErrorMiddleware` (`agent/middleware.py`) catches exceptions from any tool, including MCP tools, and returns them to the agent as `Error: tool <name> failed: ...`, so the agent can report the problem. Before each run it also checks the session for tool calls that never got a result and adds an "interrupted" result for each, because model APIs reject a conversation that contains them.

## MCP servers

MCP servers are configured in `codeasst_mcp_servers.json` at the repo root:

```json
{
  "mcp_servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "transport": "stdio"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${CWD}"],
      "transport": "stdio"
    }
  }
}
```

- Each entry under `mcp_servers` is passed to `MultiServerMCPClient` from [`langchain-mcp-adapters`](https://github.com/langchain-ai/langchain-mcp-adapters), so any connection it supports works (for example `stdio` with `command`/`args`, or `streamable_http` with `url`).
- `${VAR}` placeholders are replaced with environment variables, including those from `.env`. Missing variables become empty strings.
- `${CWD}` is set to the directory you launched CodeAsst from (unless `CWD` is already set in the environment). The filesystem server uses it as its only allowed directory. To give it access to more directories, add more paths to its `args`.
- Tools from every server are added to the agent alongside the built-in tools. Add a server here and restart CodeAsst; no code changes needed.
- Tool names must be unique across all servers and the built-in tools.
- Each `npx` server is downloaded on first use, so the first start takes longer.

## Data stored in your project

Running CodeAsst in a project creates:

- `.memory/`: session id and SQLite conversation history (git-ignored automatically)
- `.chromadb/`: local index, only when `vector_store.provider` is `chromadb`

# Public NOVA Demo

This repository is a public demonstration of the larger private
Project NOVA system.

## What this is

NOVA is a personal voice-first assistant concept. This public demo
shows a safe, reconstructed subset:

- configurable assistant runtime
- provider abstraction with online/offline/mock paths
- confirmation-gated tool execution
- lightweight prompt-injection detection
- durable memory storage
- local safe tools: web search demo, file browser, app launcher demo
- terminal REPL with real interactive commands

## What this is NOT

This is not the complete private NOVA system. It intentionally omits:

- private production orchestration
- self-editing, autostart, and unrestricted system control
- private system prompts
- complete production memory architecture
- unsafe filesystem/computer/browser control
- credentials and private endpoints

## Installation

```bash
python -m venv .venv
.venv\\Scripts\\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install .
```

Optional online provider support:

```bash
pip install ".[online]"
```

## Configuration

Copy `.env.example` to `.env` and add a Gemini API key if you want
to test the real provider:

```bash
cp .env.example .env
```

Set `NOVA_PROVIDER=gemini` to use the online provider, or leave it as
`mock` for the built-in demonstration provider.

## Usage

```bash
python -m public_nova.cli
```

Interactive REPL commands:

- `/help`
- `/quit`
- `/clear`
- `/tools`
- `/memory`
- `/audit`
- `/status`

Direct tool usage:

```
tool:web_search query=python
tool:file_list path=.
tool:memory_add text=My favorite color is teal
tool:memory_search query=color
```

## License

MIT — feel free to inspect and learn from the code.

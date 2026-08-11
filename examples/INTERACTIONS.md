# Example interactions — Public NOVA

## Terminal REPL

```text
> /help
Nova public demo REPL — available commands
...
```

```text
> /tools
Tools: app_launcher, file_list, file_read, memory_add, memory_facts, memory_search, system_status, web_search
```

```text
> tool:web_search query=python
[Demo web search result for 'python']...
```

```text
> tool:file_list path=.
[DIR] src
[DIR] tests
[FILE] README.md
...
```

## Safety demo

```text
> tool:file_controller action=delete path=/tmp/example.txt
Confirm? (yes/no): no
Action cancelled. You said: 'no'. I won't modify files without explicit confirmation.
```

## Memory demo

```text
> My favorite color is teal
# Nova extracts this into memory automatically.
> /memory
- My favorite color is teal
```

## Provider demo

```bash
# Mock provider requires no key
python -m public_nova.cli

# Online provider
NOVA_PROVIDER=gemini python -m public_nova.cli
```

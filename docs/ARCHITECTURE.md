# Public NOVA Architecture

This document explains the high-level architecture of the public NOVA
demonstration.

## Purpose

The public demo preserves the engineering concepts from the private NOVA
system without exposing unsafe production capabilities.

## Concepts demonstrated

- **Config-driven runtime** — `config.py` loads settings from environment
  variables with safe defaults.
- **Provider abstraction** — `provider.py` demonstrates the same online/
  offline/mock routing pattern used in the private project.
- **Memory** — `memory.py` demonstrates durable memory storage, retrieval,
  and lightweight memory extraction.
- **Safety** — `safety.py` demonstrates confirmation gating and lightweight
  prompt-injection detection.
- **Tool registry** — `tools.py` demonstrates safe, curated tool modules.
- **REPL** — `repl.py` demonstrates an interactive assistant loop with real
  commands and tool execution.

## Public boundaries

The public demo does not include:
- unrestricted system control
- private prompts
- complete production memory backend details
- production orchestration

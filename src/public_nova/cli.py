"""CLI entry point for the public NOVA demonstration."""

from __future__ import annotations

import argparse
import logging

from public_nova.config import NovaConfig
from public_nova.repl import NovaRepl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="public_nova", description="Public NOVA demo")
    parser.add_argument("--provider", default="mock", help="Provider: mock, gemini, ollama")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--memory-file", default="nova_memory.json", help="Memory file path")
    parser.add_argument("--audit-file", default="nova_audit.log", help="Audit log path")
    parser.add_argument("--name", default="Nova", help="Assistant name")
    parser.add_argument("--no-audit", action="store_true", help="Disable audit logging")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    config = NovaConfig(
        assistant_name=args.name,
        provider=args.provider,
        model_name=args.model,
        memory_file=args.memory_file,
        audit_file=args.audit_file,
        enable_audit=not args.no_audit,
    )
    return NovaRepl(config).start()


if __name__ == "__main__":
    raise SystemExit(main())

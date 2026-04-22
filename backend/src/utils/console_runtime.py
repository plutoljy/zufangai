from __future__ import annotations

import sys
from typing import Any


def configure_text_stream(stream: Any) -> None:
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")


def configure_console_runtime() -> None:
    configure_text_stream(sys.stdout)
    configure_text_stream(sys.stderr)

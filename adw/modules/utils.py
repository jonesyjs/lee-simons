"""utils — low-level, domain-blind file helpers operations and steps draw on."""

from pathlib import Path


def write_file(path: str, text: str) -> None:
    """Write text to a file, creating parent directories as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def read_file(path: str) -> str:
    """Read a file's text."""
    return Path(path).read_text(encoding="utf-8")

"""IDENTITY.md loader."""

from __future__ import annotations

from pathlib import Path


class IdentityLoader:
    """Loads the assistant identity/personality from IDENTITY.md."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> str:
        if self._path.exists():
            return self._path.read_text()
        return ""

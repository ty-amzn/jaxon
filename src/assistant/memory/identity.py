"""IDENTITY.md loader and writer."""

from __future__ import annotations

import aiofiles
from pathlib import Path


class IdentityLoader:
    """Loads and updates the assistant identity/personality from IDENTITY.md."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> str:
        if self._path.exists():
            return self._path.read_text()
        return ""

    async def write(self, content: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self._path, "w") as f:
            await f.write(content)

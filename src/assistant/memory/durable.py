"""Durable memory (MEMORY.md) read/write."""

from __future__ import annotations

import aiofiles
from pathlib import Path


class DurableMemory:
    """Read and write the persistent MEMORY.md file."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read(self) -> str:
        if self._path.exists():
            return self._path.read_text()
        return ""

    async def write(self, content: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self._path, "w") as f:
            await f.write(content)

    async def append(self, section: str, entry: str) -> None:
        """Append an entry under a section heading in MEMORY.md."""
        current = self.read()
        marker = f"## {section}"
        if marker in current:
            current = current.replace(
                f"{marker}\n- (none yet)",
                f"{marker}\n- {entry}",
            )
            if f"- {entry}" not in current:
                idx = current.index(marker) + len(marker)
                next_section = current.find("\n## ", idx)
                if next_section == -1:
                    current = current.rstrip() + f"\n- {entry}\n"
                else:
                    current = (
                        current[:next_section].rstrip()
                        + f"\n- {entry}\n"
                        + current[next_section:]
                    )
        else:
            current = current.rstrip() + f"\n\n{marker}\n- {entry}\n"
        await self.write(current)

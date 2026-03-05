"""Safe Python code execution tool."""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from typing import Any


async def python_exec(params: dict[str, Any]) -> str:
    """Execute Python code in an isolated temp directory."""
    code = params.get("code", "")
    timeout = min(params.get("timeout", 30), 120)  # Cap at 120s

    if not code:
        raise ValueError("No code provided")

    tmp_dir = tempfile.mkdtemp(prefix="python_exec_")
    try:
        # Write code to a temp file inside the temp directory
        script_path = f"{tmp_dir}/script.py"
        with open(script_path, "w") as f:
            f.write(code)

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmp_dir,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            return f"Execution timed out after {timeout}s"

        result_parts = []
        if stdout:
            out = stdout.decode(errors="replace")
            result_parts.append(f"stdout:\n{out}")
        if stderr:
            err = stderr.decode(errors="replace")
            result_parts.append(f"stderr:\n{err}")
        result_parts.append(f"exit_code: {proc.returncode}")

        return "\n".join(result_parts) if result_parts else "Code completed with no output"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


PYTHON_EXEC_DEF = {
    "name": "python_exec",
    "description": "Execute Python code for data analysis and calculations. Code runs in an isolated temp directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (max 120)",
                "default": 30,
            },
        },
        "required": ["code"],
    },
}

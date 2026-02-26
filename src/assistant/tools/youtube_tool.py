"""YouTube search and video info tool via yt-dlp."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 15_000


def _fmt_duration(seconds: int | float | None) -> str:
    if not seconds:
        return "Unknown"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_views(count: int | None) -> str:
    if count is None:
        return "Unknown"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


async def _run_ytdlp(*args: str, timeout: float = 30.0) -> tuple[int, str, str]:
    """Run yt-dlp with given arguments and return (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "yt-dlp", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return 1, "", "yt-dlp timed out"
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def _search(query: str, num_results: int) -> str:
    """Search YouTube and return top results."""
    rc, stdout, stderr = await _run_ytdlp(
        f"ytsearch{num_results}:{query}",
        "--flat-list", "--dump-json",
        "--no-warnings",
        timeout=30.0,
    )
    if rc != 0:
        return f"YouTube search failed: {stderr.strip()}"

    results = []
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not results:
        return f"No YouTube results for: {query}"

    parts = [f"# YouTube Search: {query}\n"]
    for i, item in enumerate(results, 1):
        title = item.get("title", "No title")
        channel = item.get("channel", item.get("uploader", "Unknown"))
        duration = _fmt_duration(item.get("duration"))
        views = _fmt_views(item.get("view_count"))
        url = item.get("url") or item.get("webpage_url") or f"https://youtube.com/watch?v={item.get('id', '')}"
        parts.append(f"## {i}. {title}")
        parts.append(f"**Channel:** {channel} | **Duration:** {duration} | **Views:** {views}")
        parts.append(f"**URL:** {url}\n")

    return "\n".join(parts)


async def _video_info(url: str) -> str:
    """Get detailed metadata for a single video."""
    rc, stdout, stderr = await _run_ytdlp(
        url,
        "--dump-json", "--no-download", "--no-warnings",
        timeout=30.0,
    )
    if rc != 0:
        return f"Failed to get video info: {stderr.strip()}"

    try:
        data = json.loads(stdout.strip().splitlines()[0])
    except (json.JSONDecodeError, IndexError):
        return "Failed to parse video metadata"

    title = data.get("title", "Unknown")
    channel = data.get("channel", data.get("uploader", "Unknown"))
    duration = _fmt_duration(data.get("duration"))
    views = _fmt_views(data.get("view_count"))
    likes = _fmt_views(data.get("like_count"))
    upload_date = data.get("upload_date", "Unknown")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    description = data.get("description", "No description")
    if len(description) > 2000:
        description = description[:2000] + "..."
    webpage_url = data.get("webpage_url", url)

    parts = [
        f"# {title}\n",
        f"**Channel:** {channel}",
        f"**Duration:** {duration}",
        f"**Views:** {views} | **Likes:** {likes}",
        f"**Uploaded:** {upload_date}",
        f"**URL:** {webpage_url}\n",
        f"## Description\n{description}",
    ]

    # Include chapters if available
    chapters = data.get("chapters")
    if chapters:
        parts.append("\n## Chapters")
        for ch in chapters[:30]:
            start = _fmt_duration(ch.get("start_time"))
            parts.append(f"- {start} — {ch.get('title', 'Untitled')}")

    return "\n".join(parts)


async def _transcript(url: str) -> str:
    """Extract subtitles/transcript from a video."""
    import tempfile
    import os
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        rc, stdout, stderr = await _run_ytdlp(
            url,
            "--write-sub", "--write-auto-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--sub-format", "vtt",
            "-o", os.path.join(tmpdir, "%(id)s.%(ext)s"),
            "--no-warnings",
            timeout=45.0,
        )
        if rc != 0:
            return f"Failed to get transcript: {stderr.strip()}"

        # Find subtitle file
        sub_file = None
        for f in Path(tmpdir).iterdir():
            if f.suffix in (".vtt", ".srt"):
                sub_file = f
                break

        if sub_file is None:
            return "No English subtitles/transcript available for this video."

        raw = sub_file.read_text(errors="replace")

    # Parse VTT: strip headers and timestamps, deduplicate lines
    lines = []
    seen = set()
    for line in raw.splitlines():
        line = line.strip()
        # Skip VTT headers, timestamps, and empty lines
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        if line.startswith("NOTE"):
            continue
        # Strip VTT tags like <c> </c> <00:00:01.000>
        import re
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        lines.append(clean)

    if not lines:
        return "No transcript content found."

    # Also get video title via the stdout JSON (yt-dlp prints info)
    # Actually re-fetch minimal info for the title
    title_parts = ["# Transcript\n"]

    transcript = " ".join(lines)
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[... transcript truncated at 15k chars ...]"

    title_parts.append(transcript)
    return "\n".join(title_parts)


async def youtube_search(params: dict[str, Any]) -> str:
    """Search YouTube, get video info, or extract transcripts.

    Args:
        params: Dictionary with 'query', 'action', and optional 'num_results'.

    Returns:
        Formatted results as markdown.
    """
    query = params.get("query", "")
    action = params.get("action", "search")
    num_results = min(params.get("num_results", 5), 10)

    if not query:
        raise ValueError("No query provided")

    if action == "search":
        return await _search(query, num_results)
    elif action == "video_info":
        return await _video_info(query)
    elif action == "transcript":
        return await _transcript(query)
    else:
        raise ValueError(f"Unknown action: {action}. Use 'search', 'video_info', or 'transcript'.")


YOUTUBE_SEARCH_TOOL_DEF = {
    "name": "youtube_search",
    "description": (
        "Search YouTube for videos, get detailed video metadata, or extract "
        "video transcripts/subtitles. Use action 'search' to find videos, "
        "'video_info' for metadata of a specific URL, or 'transcript' to read "
        "a video's spoken content."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "minLength": 1,
                "description": "Search query (for search) or video URL (for video_info/transcript)",
            },
            "action": {
                "type": "string",
                "enum": ["search", "video_info", "transcript"],
                "description": "Action to perform: search, video_info, or transcript",
                "default": "search",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of search results to return (max 10, only for search action)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

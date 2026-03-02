"""YouTube Playlist tool — registered only when youtube_playlist_enabled=true."""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

YOUTUBE_PLAYLIST_TOOL_DEF: dict[str, Any] = {
    "name": "youtube_playlist",
    "description": (
        "Manage the user's YouTube playlists. Actions:\n"
        "- list_playlists: show all playlists owned by the user\n"
        "- list_videos: list videos in a specific playlist (requires playlist_id)\n"
        "- add_video: add a video to a playlist (requires playlist_id, video_id)\n"
        "- remove_video: remove a video from a playlist (requires playlist_item_id)\n"
        "- create_playlist: create a new playlist (requires title; optional description, privacy)"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_playlists",
                    "list_videos",
                    "add_video",
                    "remove_video",
                    "create_playlist",
                ],
                "description": "The YouTube playlist action to perform.",
            },
            "playlist_id": {
                "type": "string",
                "description": "Playlist ID (for list_videos, add_video).",
            },
            "video_id": {
                "type": "string",
                "description": "YouTube video ID (for add_video).",
            },
            "playlist_item_id": {
                "type": "string",
                "description": "Playlist item ID (for remove_video). Get this from list_videos.",
            },
            "title": {
                "type": "string",
                "description": "Playlist title (for create_playlist).",
            },
            "description": {
                "type": "string",
                "description": "Playlist description (for create_playlist).",
            },
            "privacy": {
                "type": "string",
                "enum": ["private", "public", "unlisted"],
                "description": "Privacy status (for create_playlist, default: private).",
            },
            "position": {
                "type": "integer",
                "description": "Position to insert video at (for add_video, 0-indexed).",
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_yt_client: Any = None


def _get_youtube_client() -> Any:
    """Lazily create YouTubePlaylistClient."""
    global _yt_client
    if _yt_client is None:
        from assistant.core.config import get_settings
        from assistant.tools.youtube_playlist import YouTubePlaylistClient

        settings = get_settings()
        _yt_client = YouTubePlaylistClient(
            credentials_path=settings.google_auth_dir / "youtube_credentials.json",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
    return _yt_client


def set_youtube_client(client: Any) -> None:
    """Override the YouTube client (for tests)."""
    global _yt_client
    _yt_client = client


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------

async def youtube_playlist_tool(params: dict[str, Any]) -> str:
    """Handle YouTube playlist tool calls."""
    import json

    from assistant.tools.youtube_playlist import format_playlist, format_playlist_item

    client = _get_youtube_client()
    action = params.get("action", "list_playlists")

    if action == "list_playlists":
        playlists = await client.list_playlists()
        if not playlists:
            return "No playlists found."
        return json.dumps([format_playlist(p) for p in playlists], indent=2)

    elif action == "list_videos":
        playlist_id = params.get("playlist_id")
        if not playlist_id:
            return "Error: 'playlist_id' is required for list_videos."
        items = await client.list_playlist_items(playlist_id)
        if not items:
            return "Playlist is empty."
        return json.dumps([format_playlist_item(i) for i in items], indent=2)

    elif action == "add_video":
        playlist_id = params.get("playlist_id")
        video_id = params.get("video_id")
        if not playlist_id or not video_id:
            return "Error: 'playlist_id' and 'video_id' are required for add_video."
        position = params.get("position")
        item = await client.add_video(playlist_id, video_id, position=position)
        formatted = format_playlist_item(item)
        return f"Added '{formatted['title']}' to playlist (position {formatted['position']})."

    elif action == "remove_video":
        playlist_item_id = params.get("playlist_item_id")
        if not playlist_item_id:
            return "Error: 'playlist_item_id' is required for remove_video. Use list_videos to get item IDs."
        if await client.remove_video(playlist_item_id):
            return f"Removed playlist item {playlist_item_id}."
        return "Error: failed to remove video from playlist."

    elif action == "create_playlist":
        title = params.get("title")
        if not title:
            return "Error: 'title' is required for create_playlist."
        playlist = await client.create_playlist(
            title=title,
            description=params.get("description", ""),
            privacy=params.get("privacy", "private"),
        )
        formatted = format_playlist(playlist)
        return (
            f"Playlist created: '{formatted['title']}' (id: {formatted['id']}, "
            f"privacy: {formatted['privacy']})"
        )

    else:
        return f"Unknown youtube_playlist action: {action}"

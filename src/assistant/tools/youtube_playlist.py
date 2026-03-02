"""YouTube Data API v3 playlist client using httpx + google-auth."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx
from google.oauth2.credentials import Credentials

from assistant.core.http import make_httpx_client

logger = logging.getLogger(__name__)

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
SCOPES = ["https://www.googleapis.com/auth/youtube"]


class YouTubePlaylistClient:
    """Lightweight YouTube Data API v3 client for playlist management."""

    def __init__(
        self,
        credentials_path: Path,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._credentials_path = credentials_path
        self._client_id = client_id
        self._client_secret = client_secret
        self._creds: Credentials | None = None

    def _load_credentials(self) -> Credentials:
        """Load saved credentials from JSON file."""
        if not self._credentials_path.exists():
            raise FileNotFoundError(
                "YouTube credentials not found. "
                "Run `assistant youtube-auth` to authenticate."
            )
        data = json.loads(self._credentials_path.read_text())
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=self._client_id,
            client_secret=self._client_secret,
            scopes=SCOPES,
        )

    def _save_credentials(self, creds: Credentials) -> None:
        """Persist refreshed credentials."""
        self._credentials_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
        }
        self._credentials_path.write_text(json.dumps(data))

    def _ensure_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._creds is None:
            self._creds = self._load_credentials()

        if self._creds.expired and self._creds.refresh_token:
            self._do_refresh()

        return self._creds.token

    def _do_refresh(self) -> None:
        """Force-refresh the access token using the refresh token."""
        from google.auth.transport.requests import Request

        self._creds.refresh(Request())
        self._save_credentials(self._creds)
        logger.info("YouTube access token refreshed")

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an authenticated request to the YouTube API."""
        token = self._ensure_token()
        url = f"{YOUTUBE_API}{path}"
        headers = {"Authorization": f"Bearer {token}"}

        async with make_httpx_client(timeout=30) as client:
            resp = await client.request(
                method, url, headers=headers, params=params, json=json_body
            )
            # If 401, force a token refresh and retry once
            if resp.status_code == 401 and self._creds and self._creds.refresh_token:
                logger.warning("Got 401, refreshing access token and retrying")
                self._do_refresh()
                headers = {"Authorization": f"Bearer {self._creds.token}"}
                resp = await client.request(
                    method, url, headers=headers, params=params, json=json_body
                )
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    # -- Playlists -------------------------------------------------------------

    async def list_playlists(self) -> list[dict[str, Any]]:
        """List all playlists owned by the authenticated user."""
        params = {
            "part": "snippet,contentDetails",
            "mine": "true",
            "maxResults": "50",
        }
        data = await self._request("GET", "/playlists", params=params)
        return data.get("items", [])

    async def list_playlist_items(
        self, playlist_id: str, max_results: int = 50
    ) -> list[dict[str, Any]]:
        """List videos in a playlist."""
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": str(min(max_results, 50)),
        }
        data = await self._request("GET", "/playlistItems", params=params)
        return data.get("items", [])

    async def add_video(
        self, playlist_id: str, video_id: str, position: int | None = None
    ) -> dict[str, Any]:
        """Add a video to a playlist."""
        body: dict[str, Any] = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }
        if position is not None:
            body["snippet"]["position"] = position
        return await self._request(
            "POST", "/playlistItems", params={"part": "snippet"}, json_body=body
        )

    async def remove_video(self, playlist_item_id: str) -> bool:
        """Remove a video from a playlist by its playlist item ID."""
        try:
            await self._request(
                "DELETE", "/playlistItems", params={"id": playlist_item_id}
            )
            return True
        except httpx.HTTPStatusError as exc:
            logger.error("Failed to remove playlist item %s: %s", playlist_item_id, exc)
            return False

    async def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy: str = "private",
    ) -> dict[str, Any]:
        """Create a new playlist."""
        body = {
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": privacy,
            },
        }
        return await self._request(
            "POST", "/playlists", params={"part": "snippet,status"}, json_body=body
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def format_playlist(playlist: dict[str, Any]) -> dict[str, Any]:
    """Convert a YouTube playlist to a simplified dict for LLM consumption."""
    snippet = playlist.get("snippet", {})
    content = playlist.get("contentDetails", {})
    return {
        "id": playlist.get("id", ""),
        "title": snippet.get("title", "(untitled)"),
        "description": snippet.get("description", ""),
        "video_count": content.get("itemCount", 0),
        "privacy": playlist.get("status", {}).get("privacyStatus", ""),
    }


def format_playlist_item(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a YouTube playlist item to a simplified dict for LLM consumption."""
    snippet = item.get("snippet", {})
    resource = snippet.get("resourceId", {})
    return {
        "playlist_item_id": item.get("id", ""),
        "video_id": resource.get("videoId", ""),
        "title": snippet.get("title", "(untitled)"),
        "channel": snippet.get("videoOwnerChannelTitle", ""),
        "position": snippet.get("position", 0),
    }

"""Persistent state tracking for channel polling."""
import json
import time
from pathlib import Path
from typing import Optional

STATE_FILENAME = "poll_state.json"


def _get_state_path() -> Path:
    candidates = [
        Path(__file__).parent.parent / "data" / STATE_FILENAME,
        Path("/a0/usr/plugins/discord_a0/data") / STATE_FILENAME,
        Path("/a0/plugins/discord_a0/data") / STATE_FILENAME,
        Path("/git/agent-zero/usr/plugins/discord_a0/data") / STATE_FILENAME,
    ]
    for path in candidates:
        if path.exists():
            return path
    path = candidates[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_state() -> dict:
    path = _get_state_path()
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"channels": {}, "alerts": []}


def save_state(state: dict):
    from usr.plugins.discord_a0.helpers.sanitize import secure_write_json
    secure_write_json(_get_state_path(), state)


def get_last_message_id(channel_id: str) -> Optional[str]:
    state = load_state()
    return state.get("channels", {}).get(channel_id, {}).get("last_message_id")


def set_last_message_id(channel_id: str, message_id: str):
    state = load_state()
    channels = state.setdefault("channels", {})
    ch_state = channels.setdefault(channel_id, {})
    ch_state["last_message_id"] = message_id
    ch_state["last_poll"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_state(state)


def record_alert(channel_id: str, message_id: str, author: str, content: str, has_image: bool):
    state = load_state()
    alerts = state.setdefault("alerts", [])
    alerts.append({
        "channel_id": channel_id,
        "message_id": message_id,
        "author": author,
        "content": content[:500],
        "has_image": has_image,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    # Keep last 100 alerts
    state["alerts"] = alerts[-100:]
    save_state(state)


def get_poll_config(channel_id: str) -> Optional[dict]:
    state = load_state()
    return state.get("channels", {}).get(channel_id)


def add_watch_channel(channel_id: str, guild_id: str, label: str = "", owner_id: str = ""):
    state = load_state()
    channels = state.setdefault("channels", {})
    ch_state = channels.setdefault(channel_id, {})
    ch_state["guild_id"] = guild_id
    if label:
        ch_state["label"] = label
    if owner_id:
        ch_state["owner_id"] = owner_id
    save_state(state)


def get_watch_channels() -> dict:
    state = load_state()
    return state.get("channels", {})


def remove_watch_channel(channel_id: str):
    state = load_state()
    state.get("channels", {}).pop(channel_id, None)
    save_state(state)

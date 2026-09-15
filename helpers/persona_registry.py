import json
import time
from pathlib import Path
from typing import Optional

REGISTRY_FILENAME = "persona_registry.json"


def _get_registry_path() -> Path:
    """Resolve registry path within the plugin's data directory."""
    candidates = [
        Path(__file__).parent.parent / "data" / REGISTRY_FILENAME,
        Path("/a0/usr/plugins/discord_a0/data") / REGISTRY_FILENAME,
        Path("/a0/plugins/discord_a0/data") / REGISTRY_FILENAME,
        Path("/git/agent-zero/usr/plugins/discord_a0/data") / REGISTRY_FILENAME,
    ]
    for path in candidates:
        if path.exists():
            return path
    # Default to first, create dirs
    path = candidates[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_registry() -> dict:
    path = _get_registry_path()
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {"users": {}, "updated_at": None}


def save_registry(registry: dict):
    registry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    from usr.plugins.discord_a0.helpers.sanitize import secure_write_json
    secure_write_json(_get_registry_path(), registry)


def upsert_user(
    user_id: str,
    username: str,
    display_name: Optional[str] = None,
    roles: Optional[list[str]] = None,
    guild_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    registry = load_registry()
    users = registry.setdefault("users", {})
    existing = users.get(user_id, {})
    existing["username"] = username
    if display_name:
        existing["display_name"] = display_name
    existing["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if guild_id:
        guilds = existing.setdefault("guilds", {})
        guild_info = guilds.setdefault(guild_id, {})
        if roles is not None:
            guild_info["roles"] = roles

    if notes:
        existing_notes = existing.get("notes", "")
        if notes not in existing_notes:
            existing["notes"] = (existing_notes + "\n" + notes).strip()

    users[user_id] = existing
    save_registry(registry)
    return existing


def get_user(user_id: str) -> Optional[dict]:
    registry = load_registry()
    return registry.get("users", {}).get(user_id)


def search_users(query: str, guild_id: Optional[str] = None) -> list[dict]:
    registry = load_registry()
    results = []
    q = query.lower()
    for uid, data in registry.get("users", {}).items():
        match = (
            q in data.get("username", "").lower()
            or q in data.get("display_name", "").lower()
            or q in data.get("notes", "").lower()
        )
        if match:
            if guild_id and guild_id not in data.get("guilds", {}):
                continue
            results.append({"user_id": uid, **data})
    return results


def get_guild_users(guild_id: str) -> list[dict]:
    registry = load_registry()
    return [
        {"user_id": uid, **data}
        for uid, data in registry.get("users", {}).items()
        if guild_id in data.get("guilds", {})
    ]


def format_user_profile(user_data: dict) -> str:
    lines = [f"Username: {user_data.get('username', 'Unknown')}"]
    if user_data.get("display_name"):
        lines.append(f"Display Name: {user_data['display_name']}")
    if user_data.get("user_id"):
        lines.append(f"User ID: {user_data['user_id']}")
    if user_data.get("last_seen"):
        lines.append(f"Last Seen: {user_data['last_seen']}")

    guilds = user_data.get("guilds", {})
    if guilds:
        lines.append("Servers:")
        for gid, ginfo in guilds.items():
            roles = ginfo.get("roles", [])
            lines.append(f"  - Guild {gid}: roles=[{', '.join(roles)}]")

    if user_data.get("notes"):
        lines.append(f"Notes: {user_data['notes']}")
    return "\n".join(lines)

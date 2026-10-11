"""Offline: /opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_poll_workflow."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from usr.plugins.discord_a0.helpers.workflows import discord_poll as poll


CONFIG = {"bot_id": "default", "bot": {"token": "test-token", "enabled": True}, "servers": []}
CHANNEL = "123456789012345678"


def message(mid, content, attachments=None, embeds=None):
    return {
        "id": mid,
        "content": content,
        "timestamp": "2026-01-01T00:00:00.000000+00:00",
        "author": {"id": "456", "username": "Reporter", "global_name": "Reporter"},
        "attachments": attachments or [],
        "embeds": embeds or [],
    }


def make_tool(args):
    agent = SimpleNamespace(hist_add_message=Mock())
    tool = poll.DiscordPoll(agent=agent, name="discord_poll", method=None, args=args,
                            message="", loop_data=None)
    tool.set_progress = AsyncMock()
    return tool


def poll_patches(watches, client, recorded, state):
    return (
        patch.object(poll, "get_discord_config", return_value=CONFIG),
        patch.object(poll, "require_auth"),
        patch.object(poll, "get_modes_to_try", return_value=["bot"]),
        patch.object(poll, "get_watch_channels", return_value=watches),
        patch.object(poll, "get_last_message_id", return_value=None),
        patch.object(poll, "set_last_message_id", side_effect=lambda cid, mid: state.__setitem__(cid, mid)),
        patch.object(poll, "record_alert", side_effect=lambda *a, **k: recorded.append(a)),
        patch.object(poll, "_save_to_memory", new_callable=AsyncMock),
        patch.object(poll.DiscordClient, "from_config", return_value=client),
    )


async def main():
    # 1. No watched channels.
    tool = make_tool({"action": "check"})
    with patch.object(poll, "get_discord_config", return_value=CONFIG), \
         patch.object(poll, "require_auth"), \
         patch.object(poll, "get_watch_channels", return_value={}):
        result = await tool.execute()
    assert "No channels being watched" in result.message, result.message

    # 2. New messages produce alerts and advance the cursor.
    recorded, state = [], {}
    client = SimpleNamespace(
        get_all_channel_messages=AsyncMock(return_value=[
            message("300", "newest message"),
            message("200", "older message"),
        ]),
        close=AsyncMock(),
    )
    tool = make_tool({"action": "check"})
    patches = poll_patches({CHANNEL: {"label": "alerts", "owner_id": ""}}, client, recorded, state)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
        result = await tool.execute()
    assert "Found 2 new alert(s)" in result.message, result.message
    assert [r[1] for r in recorded] == ["200", "300"], "alerts must be recorded oldest-first"
    assert state[CHANNEL] == "300", "cursor must advance to the newest message"
    client.close.assert_awaited_once()

    # 3. Image attachments are loaded and reported.
    recorded, state = [], {}
    client = SimpleNamespace(
        get_all_channel_messages=AsyncMock(return_value=[
            message("400", "chart attached", attachments=[{
                "filename": "chart.png", "url": "https://cdn.discordapp.com/attachments/1/2/chart.png",
            }]),
        ]),
        close=AsyncMock(),
    )
    tool = make_tool({"action": "check"})
    patches = poll_patches({CHANNEL: {"label": "alerts", "owner_id": ""}}, client, recorded, state)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8], \
         patch.object(poll.DiscordPoll, "_load_image", new_callable=AsyncMock, return_value=True) as loader:
        result = await tool.execute()
    assert "1 image(s) loaded for analysis" in result.message, result.message
    loader.assert_awaited_once()
    assert loader.call_args.args[0] == "https://cdn.discordapp.com/attachments/1/2/chart.png"
    assert recorded[0][4] is True, "has_image must be recorded"

    # 4. No new messages.
    client = SimpleNamespace(get_all_channel_messages=AsyncMock(return_value=[]), close=AsyncMock())
    tool = make_tool({"action": "check"})
    patches = poll_patches({CHANNEL: {}}, client, [], {})
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
        result = await tool.execute()
    assert "No new alerts" in result.message, result.message

    # 5. Watch/unwatch validate snowflakes; list reports watches.
    added, removed = [], []
    tool = make_tool({"action": "watch", "channel_id": "not-a-snowflake"})
    assert "Invalid channel_id" in (await tool.execute()).message
    tool = make_tool({"action": "watch", "channel_id": CHANNEL, "owner_id": "999999999999999999"})
    with patch.object(poll, "add_watch_channel", side_effect=lambda *a: added.append(a)):
        assert "Now watching" in (await tool.execute()).message
    assert added and added[0][0] == CHANNEL and added[0][3] == "999999999999999999"
    tool = make_tool({"action": "watch", "channel_id": CHANNEL, "owner_id": "bad"})
    assert "Invalid owner_id" in (await tool.execute()).message
    tool = make_tool({"action": "unwatch", "channel_id": "bad"})
    assert "Invalid channel_id" in (await tool.execute()).message
    tool = make_tool({"action": "unwatch", "channel_id": CHANNEL})
    with patch.object(poll, "remove_watch_channel", side_effect=lambda cid: removed.append(cid)):
        assert "Stopped watching" in (await tool.execute()).message
    assert removed == [CHANNEL]
    tool = make_tool({"action": "list"})
    with patch.object(poll, "get_watch_channels", return_value={CHANNEL: {"label": "alerts", "guild_id": "789"}}):
        listed = await tool.execute()
    assert "Watching 1 channel(s)" in listed.message and "alerts" in listed.message
    tool = make_tool({"action": "bogus"})
    assert "Unknown action" in (await tool.execute()).message

    # 6. The image loader rejects non-CDN URLs before any download.
    tool = make_tool({"action": "check"})
    assert await tool._load_image("https://evil.example.com/x.png", None, "Reporter", "ctx") is False

    # 7. Scheduler setup rejects a non-numeric interval.
    tool = make_tool({"action": "setup_scheduler", "interval": "soon"})
    assert "Invalid interval" in (await tool.execute()).message
    scheduler = SimpleNamespace(add_task=AsyncMock())
    tool = make_tool({"action": "setup_scheduler", "interval": "30"})
    with patch("helpers.task_scheduler.TaskScheduler.get", new_callable=AsyncMock, return_value=scheduler):
        scheduled = await tool.execute()
    assert "polling every 30 minutes" in scheduled.message, scheduled.message
    scheduler.add_task.assert_awaited_once()

    print("PASS: poll check alerts, cursor advance, image loading, watch state validation, SSRF guard and scheduler intervals")


if __name__ == "__main__":
    asyncio.run(main())

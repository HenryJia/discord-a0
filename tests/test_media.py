"""Offline: /opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_media."""
import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from usr.plugins.discord_a0.helpers import discord_bot as bridge


class Attachment:
    def __init__(self, filename, content_type, data):
        self.filename = filename
        self.content_type = content_type
        self.size = len(data)
        self._data = data

    async def read(self):
        return self._data


class FakeTask:
    def __init__(self, value):
        self._value = value

    async def result(self):
        return self._value


async def main():
    bot = bridge.ChatBridgeBot("test-token")
    bot._connection.user = SimpleNamespace(id=123)
    channel_id = "123456789012345678"
    channel = SimpleNamespace(id=int(channel_id), typing=nullcontext, send=AsyncMock())
    oversize = bot.MAX_ATTACHMENT_BYTES + 1
    message = SimpleNamespace(
        id=1001, content="<@123> look at these", channel=channel,
        guild=SimpleNamespace(id=789), reference=None,
        attachments=[
            Attachment("chart.png", "image/png", b"PNGDATA"),
            Attachment("report.pdf", "application/pdf", b"PDFDATA"),
            Attachment("notes.md", "text/markdown", b"# notes\n"),
            Attachment("archive.zip", "application/zip", b"ZIPDATA"),
            Attachment("noext", "application/octet-stream", b"RAW"),
            Attachment("huge.png", "image/png", b"x" * oversize),
        ],
        author=SimpleNamespace(id=456, bot=False, display_name="Tester", name="Tester"),
    )
    config = {"bot_id": "default", "bot": {"token": "test-token"}, "servers": []}
    captured, existed = [], []

    def communicate(user_msg):
        captured.append(user_msg)
        existed.extend(Path(path).exists() for path in user_msg.attachments)
        return FakeTask("ok")

    context = SimpleNamespace(id="media-test", communicate=communicate)
    try:
        with patch.object(bot, "_get_config", return_value=config), \
             patch.object(bot, "_has_tool_access", return_value=True), \
             patch("helpers.message_queue.log_user_message"):
            result = await bot._get_full_agent_response(channel_id, "look at these", message, context=context)
        assert result == "ok"
        assert len(captured) == 1
        paths = captured[0].attachments
        assert len(paths) == 3, f"images plus allowed documents only, got {paths}"
        suffixes = sorted(Path(path).suffix for path in paths)
        assert suffixes == [".md", ".pdf", ".png"], suffixes
        assert all(existed), "attachments must exist while the agent processes them"
        assert not any(Path(path).exists() for path in paths), "per-request temp files must be cleaned up"

        # The read-only path never forwards attachments.
        captured.clear()
        with patch.object(bot, "_get_config", return_value=config), \
             patch.object(bot, "_has_tool_access", return_value=False), \
             patch.object(bot, "_get_agent_response", new_callable=AsyncMock, return_value="read only") as restricted:
            assert await bot._get_full_agent_response(channel_id, "x", message, context=context) == \
                "Web UI approval is required for full agent access in this channel."
            restricted.assert_not_awaited()
        assert not captured, "Unapproved requests must not build a user message"
        print("PASS: image and document attachments reach approved agent input, disallowed and oversize files are skipped, temp files are cleaned up, and the read-only path is unaffected")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

# Discord A0 setup

## Install

In Agent Zero's Plugin Installer, use https://github.com/3clyp50/discord-a0.
The framework installs the plugin under `usr/plugins/discord_a0`, runs its
installation hook and makes **Config** available. There is no separate dashboard.
No compatibility symlink under `plugins/` is needed.

The installation hook uses the framework interpreter to prepare `aiohttp`,
`PyYAML` and `discord.py`, and mirrors the `discord-a0-*` skills into `usr/skills`.

If replacing another Discord plugin, stop and disable it first. Do not run the
same bot token through both plugins. This version does not import settings,
access approvals or existing chat mappings automatically.

## Connect a bot

1. Create an application and bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Enable Message Content Intent. Enable Server Members Intent when member reads are needed.
3. Invite it with View Channels, Read Message History and Send Messages. Include Attach Files for uploads and Add Reactions for reactions.
4. Open **Discord A0 > Config**, add a bot and enter its token.
5. Set server/user allowlists, instructions, model preset and profile as needed.
6. Save, then use the bot row's Start/Stop and Restart icons. Connected status confirms the Gateway connection.

Repeat for additional bots, each with a distinct token. Keep Gateway settings
under Global / All profiles; scoped settings affect agent tools.

## Conversations and access

Mention the bot or reply to one of its messages. Channel registration is only
needed when the bot should receive every message in a channel.

The initial mode is read-only Discord access. To allow agent tools, contact the
bot once, then approve the exact user/server/channel in **Config > Agent access**.
Timed and Until revoked approvals survive restarts. They do not bypass allowlists
or tool policy. No authentication key is sent through Discord.

`DISCORD_BOT_TOKEN` overrides the bot with ID `default`. The optional
`DISCORD_USER_TOKEN` is restricted to ordinary read operations and is never a
fallback for the member-scoped bridge. Prefer bot credentials; user-token use
may violate Discord's terms.

Tokens and runtime state are private. Never commit or share `config.json`, `data/`
or credentials. See [Chat Bridge Guide](CHAT_BRIDGE.md) for delivery, search,
approvals, commands and their limits.

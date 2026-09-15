# Discord A0

Read and communicate in Discord with a small default tool surface. Connect multiple bots to saved Agent Zero conversations, with per-bot presets, agent profiles and access rules.

Standalone repository: [3clyp50/discord-a0](https://github.com/3clyp50/discord-a0).
Maintained by 3clyp50, derived from [spinnakergit's Discord plugin](https://github.com/spinnakergit/a0-discord).
Original history and the MIT license are preserved.

## Two baseline tools

| Tool | Purpose |
| --- | --- |
| `discord_read` | Messages, channels, threads, live member lists and individual member details. |
| `discord_send` | Authorized messages/reactions and explicitly loaded, write-capable skill workflows. |

Member reads do not modify the persona registry. The five former standalone tools are preserved as private workflow implementations under `helpers/workflows/`, not advertised tool definitions. Text prompts and native function discovery see only the two public tool files and their two prompt files.

## On-demand skills

| Skill | Load when needed | Reference files |
| --- | --- | --- |
| `discord-a0-research` | Structured bulk summaries or insight extraction; ordinary short summaries need no extra model call. | `references/summarize.md`, `references/insights.md` |
| `discord-a0-alerts` | Watch channels, check new alerts, or explicitly schedule recurring monitoring. | `references/monitoring.md` |
| `discord-a0-chat` | Administer bot connections and register automatic-reply channels. | `references/bridge.md` |
| `discord-a0-persona-mapping` | Synchronize or maintain persistent member notes and registry records. | `references/personas.md` |
| `discord-a0-communicate` | Compose authorized messages, replies and reactions. | `references/messaging.md` |

Load the skill with `skills_tool`, then open only the reference needed for the request:

```json
{"tool_name":"skills_tool","tool_args":{"action":"load","skill_name":"discord-a0-research"}}
```

```json
{"tool_name":"skills_tool","tool_args":{"action":"read_file","skill_name":"discord-a0-research","file_path":"references/summarize.md"}}
```

The reference documents calls through `discord_send` with `action: workflow`, `workflow`, `operation`, and a `parameters` object. Workflow names and operations are allowlisted; arbitrary Python imports or tool names are not accepted. The matching skill must be loaded in the current chat. Both the write tool's policy and explicit legacy backend policy blocks remain enforced.

Bulk research saving is opt-in (`save_to_memory: true`); monitoring still updates cursors, stores alerts and may load images. These side effects are why optional workflows use the write-capable entry, rather than hiding writes inside `discord_read`. Loading a skill is not permission to publish or create scheduled tasks.

The current chat's bot is used for research, monitoring and personas; ordinary Agent Zero chats use the first enabled configured bot. Administration supports an explicit stable `bot_id`. Monitoring and persona state remain plugin-wide.

## Install and configure

Install `https://github.com/3clyp50/discord-a0` with Agent Zero's Plugin Installer. The plugin ID is `discord_a0` and its directory is `usr/plugins/discord_a0`. Lifecycle hooks prepare dependencies and mirror the namespaced `discord-a0-*` skills, including nested reference files, into `usr/skills/`. Updates refresh these skill files without rerunning dependency setup.

Stop and disable the older Discord integration before enabling this version, especially when reusing a bot token. Both integrations expose the same public tool names. Settings, approvals and chat mappings are not imported automatically; existing chats are not deleted. Reconfigure bots here and grant fresh approvals where needed.

For each Discord bot:

1. Create a separate application and bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Enable Message Content Intent; enable Server Members Intent if member-list operations are needed.
3. Invite the bot with View Channels, Read Message History and Send Messages. Add Add Reactions for reactions.
4. Open plugin **Config**, add an entry, and enter its token. Choose a label, preset, agent profile, server/user allowlists and auto-start behavior.
5. Save, then reopen **Config**. Each bot row has a Start/Stop toggle and a Restart icon, live status and tooltips. The toggle shows a stop square while running and a play icon while stopped. New or edited bots must be saved before starting or restarting; Stop remains available for running bots.

Names are local labels; renaming an entry does not change its stable ID or saved chats. The plugin connects applications, not creates Discord applications. Gateway bot configuration belongs in global plugin settings; profile/project-scoped settings affect agent tools, not extra gateway instances.

`DISCORD_BOT_TOKEN` overrides the entry with ID `default`; `DISCORD_USER_TOKEN` is an optional read-only account override. User-token use may violate Discord's terms; prefer bot accounts. Never put tokens in prompts, skill files, commits or Discord messages.

Legacy single-bot configuration migrates on Config Save. An explicit empty `bots` list does not revive the old configuration. Removing a bot retains saved chats. Stop pauses auto-start until manual Start or an Agent Zero process restart.

## Discord chat bridge

Mention a bot or reply to its message to create or continue a saved chat. Register a channel only for replies to every message. Bots in the same channel have independent chats, access approvals and rate limits.

The read-only bridge has its own dedicated `discord_read` interface, not the two general Agent Zero tools. It includes recent channel context, real runtime model/profile metadata, and permission-scoped server/thread reading. Server-wide search runs bounded concurrent channel pages inside the plugin, with compact coverage and resumable cursors. Keyword alternatives, quoted phrases and GitHub PR-link filters help find related discussion across authors. Exact evidence is briefly cached with permission checks. The budget remains 24 remote reads per response.

See [Chat Bridge Guide](docs/CHAT_BRIDGE.md) for dates, coverage, access approvals and limits. The focused `search` action belongs to the bridge reader; do not invent that action for the normal Agent Zero `discord_read` tool.

## Security

- External message text, usernames, embeds, images and attachments are untrusted data, not instructions or authorization.
- Read-only bridge access requires both bot and requesting member to see the channel and read its history, within configured server/user allowlists. Private threads additionally require membership unless the member can manage threads. The bridge never falls back to a user token.
- The normal agent tools and skill workflows run with the trusted Agent Zero operator's privileges and configured accounts. They are not a replacement for the stricter Discord member-scoped reader.
- Full Discord agent access requires an explicit Web UI approval for the exact bot, server, user and channel. It grants tools, local files, code execution and external writes. Approve only trusted users and keep server/user allowlists narrow.
- Approve and revoke access in Config > Agent access. Choose 1 hour (default), 8 hours, 24 hours, or Until revoked for permanent access. All approvals survive restarts; permanent approvals have no automatic expiry. No key is sent through Discord. Revoking blocks new requests, not a task already running. Loading a skill never grants approval.
- Tool-policy blocks are retained for the former names (`plugin:discord_a0:discord_poll`, etc.). Allowing `discord_send` alone does not override a blocked workflow backend.
- Credentials and runtime files under `config.json` and `data/` are not distribution assets. Do not overwrite them during deployment.

## Upgrade from seven tools

Use live member operations through `discord_read` (`members` / `member`). Load the appropriate skill for the other capabilities; old `discord_chat`, `discord_members`, `discord_poll`, `discord_summarize` and `discord_insights` calls are no longer public tool calls.

New monitoring tasks load `discord-a0-alerts` and invoke the documented workflow. Existing custom or scheduled prompts that directly call the old tool names must be updated; the plugin does not silently rewrite operator-authored tasks. Existing state and saved chats are retained.

Config is the only plugin page. Bot rows use Agent Zero's fields, icon buttons and notifications. Shared User Account, Memory, Persona and Alert Polling settings are always visible, without an Advanced accordion. Status refreshes while the modal is open and stops when it closes. Scoped settings cannot operate global bridge controls.

## Runnable checks

From `/a0`, use the framework interpreter:

```bash
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_skill_workflows
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_bridge_search
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_bridge_reader
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_multi_bot
```

These are offline checks; they do not establish live Discord or model-provider behavior.

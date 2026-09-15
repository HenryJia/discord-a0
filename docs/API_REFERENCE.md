# API Reference

Internal REST API endpoints exposed by the Discord plugin for the Agent Zero WebUI.

---

## Connection Test

### `GET|POST /api/plugins/discord_a0/discord_test`

Test the Discord connection using the configured token.

**Response (success):**
```json
{
  "ok": true,
  "user": "MyBot",
  "mode": "bot",
  "id": "1234567890123456789"
}
```

**Response (failure):**
```json
{
  "ok": false,
  "error": "Bot token not configured. Set DISCORD_BOT_TOKEN env var or configure in Discord plugin settings."
}
```

---

## Configuration

### `GET /api/plugins/discord_a0/discord_config_api`

Get the current plugin configuration. Tokens are masked for security (first 4 + last 4 characters shown).

**Response:**
```json
{
  "bot": {
    "token": "MTIz...wxyz"
  },
  "user": {
    "token": "",
    "read_only": true
  },
  "servers": ["1234567890123456789"],
  "defaults": {
    "message_limit": 100,
    "insight_limit": 200,
    "member_sync_limit": 1000
  },
  "memory": {
    "auto_save_summaries": true,
    "auto_save_insights": true,
    "export_format": "markdown"
  },
  "persona": {
    "auto_sync_on_read": false,
    "track_activity": true
  }
}
```

### `POST /api/plugins/discord_a0/discord_config_api`

Update the plugin configuration. Masked tokens (containing `...`) are preserved from the existing config to prevent accidental overwrites.

**Note:** These API endpoints have CSRF protection disabled, so they can be called directly with `curl` or `fetch()` without needing a CSRF token.

**Request body:** Same shape as the GET response, with actual token values.

**Response:**
```json
{
  "ok": true
}
```

---

## Discord REST API Endpoints Used

The plugin communicates with Discord's v10 REST API. Here are the endpoints it calls:

| Plugin Operation | Discord API Endpoint | Method |
|-----------------|---------------------|--------|
| List channels | `/guilds/{id}/channels` | GET |
| Get channel info | `/channels/{id}` | GET |
| Read messages | `/channels/{id}/messages` | GET |
| Active threads | `/guilds/{id}/threads/active` | GET |
| Archived threads | `/channels/{id}/threads/archived/public` | GET |
| Send message | `/channels/{id}/messages` | POST |
| Add reaction | `/channels/{id}/messages/{id}/reactions/{emoji}/@me` | PUT |
| List members | `/guilds/{id}/members` | GET |
| Get member | `/guilds/{id}/members/{id}` | GET |
| Search messages | `/guilds/{id}/messages/search` | GET |
| Current user | `/users/@me` | GET |
| User guilds | `/users/@me/guilds` | GET |

### Rate Limiting

The plugin tracks Discord's rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset-After`) per endpoint bucket and automatically waits when limits are reached. On 429 responses, it retries after the specified `retry_after` delay.

### Pagination

Message fetching supports automatic pagination for limits exceeding 100 (Discord's per-request maximum). The `get_all_channel_messages()` method batches requests using the `before` parameter until the requested limit is reached or no more messages are available.

---

## Persona Registry Data Format

The persona registry is stored at `data/persona_registry.json` within the plugin directory.

**Schema:**
```json
{
  "users": {
    "USER_ID": {
      "username": "alice",
      "display_name": "Alice Developer",
      "last_seen": "2026-03-05T14:30:00Z",
      "guilds": {
        "GUILD_ID": {
          "roles": ["role_id_1", "role_id_2"]
        }
      },
      "notes": "Lead smart contract developer. Expert in Solidity.\nActive in #dev-chat and #code-review."
    }
  },
  "updated_at": "2026-03-05T14:30:00Z"
}
```

Notes are append-only — calling `discord_members` with `action: note` adds to existing notes rather than replacing them. Duplicate notes are detected and skipped.

---

## Poll State Data Format

The polling state is stored at `data/poll_state.json` within the plugin directory.

**Schema:**
```json
{
  "channels": {
    "CHANNEL_ID": {
      "guild_id": "YOUR_SERVER_ID",
      "label": "alerts",
      "owner_id": "9876543210",
      "last_message_id": "1341900000000000000",
      "last_poll": "2026-03-05T14:30:00Z"
    }
  },
  "alerts": [
    {
      "channel_id": "YOUR_CHANNEL_ID",
      "message_id": "1341900000000000001",
      "author": "ServerOwner",
      "content": "BTC looking strong here. Target 1: 72,500...",
      "has_image": true,
      "timestamp": "2026-03-05T14:30:00Z"
    }
  ]
}
```

### Field Reference

**channels (watched channels):**

| Field | Description |
|-------|-------------|
| `guild_id` | Server this channel belongs to |
| `label` | Friendly name for display |
| `owner_id` | Only track messages from this user (empty = all users) |
| `last_message_id` | Last message ID seen — next poll fetches messages after this |
| `last_poll` | Timestamp of the most recent poll |

**alerts (alert history):**

| Field | Description |
|-------|-------------|
| `channel_id` | Which watched channel this came from |
| `message_id` | Discord message ID |
| `author` | Display name of the message author |
| `content` | First 500 characters of the message |
| `has_image` | Whether image attachments were found and analyzed |
| `timestamp` | When the alert was recorded |

The alert history keeps the last 100 entries. Older alerts are pruned automatically.

### Resetting Poll State

To re-poll from scratch (e.g., to re-fetch older messages), delete `data/poll_state.json`. The next poll will fetch the most recent messages and establish a new baseline.

To reset a single channel, remove its entry from the `channels` object in the JSON file.

---

## Image Analysis Pipeline

When the `discord_poll` tool encounters image attachments in alerts, it processes them through this pipeline:

```
Discord Message (with attachment)
    ↓
Download image from Discord CDN (aiohttp GET)
    ↓
Compress (helpers/images.compress_image)
  - Max 768,000 pixels
  - JPEG quality 75
    ↓
Base64 encode
    ↓
Build multimodal content:
  [
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
    {"type": "text", "text": "Analyze this image: identify targets, levels..."}
  ]
    ↓
Inject into agent history (helpers/history.RawMessage)
    ↓
LLM sees image in next loop iteration → analyzes it
```

**Supported image formats:** PNG, JPG, JPEG, GIF, WEBP

**Sources checked:**
- Message attachments (files uploaded directly)
- Embed images (linked images that Discord auto-embeds)
- Embed thumbnails

**Requirements:**
- The main chat model must support **multimodal/vision** input
- Models that work: GPT-4o, Claude (Opus/Sonnet with vision), Gemini Pro Vision
- Text-only models will receive the image data but cannot interpret it

---

## Memory Integration

### Auto-Save Format

When summaries and insights are saved to Agent Zero's memory, they follow this format:

**Summaries:**
```
Discord Summary - #channel-name (guild: 1234567890) [2026-03-05 14:30, 100 messages]

### Summary
[generated summary content]

### Key Topics
[...]
```

**Insights:**
```
Discord Insights - #channel-name (guild: 1234567890) [focus: tokenomics] [2026-03-05 14:30, 200 messages analyzed]

### Overarching Themes
[generated insight content]

### Key Ideas & Concepts
[...]
```

**Alerts:**
```
Discord Alerts [2026-03-05 14:30]

[2026-03-05 14:30] ServerOwner in #alerts: BTC looking strong here.
  Target 1: 72,500  Target 2: 74,000. Invalidation below 69,800.
  Images: chart_btc_targets.png
```

---

## Chat Bridge State Data Format

The chat bridge state is stored at `data/chat_bridge_state.json` within the plugin directory.

**Schema:**
```json
{
  "channels": {
    "CHANNEL_ID": {
      "guild_id": "YOUR_SERVER_ID",
      "label": "llm-chat",
      "added_at": "2026-03-05T14:30:00Z"
    }
  },
  "contexts": {
    "CHANNEL_ID": "context-uuid-string"
  }
}
```

### Field Reference

**channels (designated chat channels):**

| Field | Description |
|-------|-------------|
| `guild_id` | Server this channel belongs to |
| `label` | Friendly name for display |
| `added_at` | When the channel was registered |

**contexts (Agent Zero conversation contexts):**

| Field | Description |
|-------|-------------|
| Key | Channel ID |
| Value | Agent Zero context UUID for conversation continuity |

Contexts are created automatically when the first message arrives in a channel. They persist across bot restarts (the context ID is stored, and Agent Zero can resume the conversation if the context still exists in memory).

### Resetting Chat Bridge State

To reset all chat channels and contexts, delete `data/chat_bridge_state.json`. You'll need to re-add channels after the reset.

To reset a single channel's conversation (start fresh), remove its entry from the `contexts` object. The next message will create a new conversation context.

---

### Memory Metadata

Saved memory entries include metadata for retrieval:
- `area`: `"main"`
- `source`: `"discord_summarize"`, `"discord_insights"`, or `"discord_poll"`

### Fallback Storage

If the memory plugin isn't available, files are written to:
- `memory/discord_summaries/summary_YYYYMMDD_HHMMSS.md`
- `memory/discord_insights/insights_YYYYMMDD_HHMMSS.md`
- `memory/discord_alerts/alert_YYYYMMDD_HHMMSS.md`

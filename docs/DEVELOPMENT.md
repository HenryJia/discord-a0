# Discord A0 development

The standalone source is https://github.com/3clyp50/discord-a0. The framework plugin
ID is `discord_a0`, and its installed directory is `usr/plugins/discord_a0`.

- `hooks.py` owns installation, configuration validation and skill mirroring.
- `helpers/discord_bot.py` owns Gateway lifecycle, chats and approval enforcement.
- `helpers/discord_client.py` owns configuration selection and REST requests.
- `helpers/delivery.py` owns attachment delivery and per-request final receipts.
- `tools/` exposes `discord_read` and `discord_send`; optional workflows stay private.
- `skills/discord-a0-*/` contains namespaced skills and reference files.
- `webui/config.html` and `webui/discord-store.js` own the Config page and controls.

Use `usr.plugins.discord_a0` imports and `/plugins/discord_a0/` HTTP routes.
The third-party SDK remains `import discord`, and the core command integration
selector remains `integration='discord'`. No symlink or compatibility module is needed.

Do not commit runtime settings, credentials, chat state or generated test output.
Use the framework interpreter for backend checks, not the agent execution environment.

```bash
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_skill_workflows
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_delivery
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_reply_delivery
/opt/venv-a0/bin/python -m usr.plugins.discord_a0.tests.test_access_approvals
node --test usr/plugins/discord_a0/tests/test_config_store.mjs
```

These offline checks do not establish live Discord or model-provider behavior.

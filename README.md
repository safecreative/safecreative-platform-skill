# Safe Creative Platform for AI coding agents

An [Agent Skill](https://agentskills.io) that teaches coding agents (Claude Code, Codex, GitHub Copilot, Cursor, Gemini CLI,
Windsurf, JetBrains and others) to integrate the [Safe Creative Platform](https://platform.safecreative.org) API correctly:
registering events with a qualified timestamp, idempotent retries with `client_ref`, hash-only digests, certifications,
error codes, test keys and webhook signature verification.

```
skills/safecreative-platform-skill/
├── SKILL.md                      what the agent reads first
├── references/                   registering events, certifications, webhooks, errors and limits, test mode
└── scripts/                      sc_api.py (minimal client), sc_hash.py, sc_verify_webhook.py — Python 3.9+, no dependencies
```

The same folder is packaged for each kind of client:

| File | For |
|---|---|
| `plugin.json` | [Agent Plugins 1.0](https://agent-plugins.org) clients (Codex, Cursor, GitHub Copilot / VS Code, Kiro…) |
| `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Claude Code plugin and marketplace |

## Install

- **Any agent** (copies the skill to each installed agent's skills folder):
  `npx skills add safecreative/safecreative-platform-skill`
- **Claude Code**: `/plugin marketplace add safecreative/safecreative-platform-skill` and then `/plugin install safecreative-platform@safecreative`
- **claude.ai**: upload a ZIP of `skills/safecreative-platform-skill` in Settings › Capabilities.
- **By hand**: copy `skills/safecreative-platform-skill` into your agent's skills folder: `.agents/skills/` (Codex, Copilot,
  Cursor, Gemini CLI, Windsurf…), `.claude/skills/` (Claude Code), `.github/skills/` (Copilot).

Then give your agent a test key, never a live one while developing:

```
export SC_API_KEY=sc_test_...        # created in https://platform.safecreative.org/console
```

## Development

Safe Creative maintains the skill alongside the platform and publishes each version here; issues and suggestions are
welcome. The code samples in `references/` and the scripts are tested against the API. Before publishing a change:

```
claude plugin validate --strict .
```

Keep `SKILL.md` free of client-specific instructions and within the Agent Skills specification (only `name`, `description`,
`license`, `compatibility`, `metadata` and `allowed-tools` in the front matter).

## License

Apache License 2.0 — Copyright 2026 Safe Creative S.L. See `LICENSE` and `NOTICE`. The license does not grant rights to
the Safe Creative trademarks.

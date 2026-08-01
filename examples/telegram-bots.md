---
title: Telegram Bots
kicker: broken branch · field guide
dek: everything BotFather won't tell you twice
theme: field-guide
profile: laser
fit: 1
columns: auto
footer: Broken Branch · field guide · printed by Loam
---

## Make a brand new bot

<!--steps-->
1. **Find the REAL BotFather** — search `@BotFather`, take the one with the blue check. Impersonators exist and they would love your token.
2. **Say the magic word** — `/newbot`
3. **Display name** — free-form, changeable later. e.g. `Broken Branch Zomboid`
4. **Username** — globally unique, MUST end in `bot`. e.g. `bb_zomboid_bot`. *Not* freely changeable afterwards — choose like you mean it.
5. **Catch the token** — `123456789:AAH-xxxxxxxxxxxxxxxxxxxx`. Copy it somewhere safe before the chat scrolls.
6. **Grab your chat id** — message the bot once, then `curl https://api.telegram.org/bot<TOKEN>/getUpdates` and read `message.chat.id`.

> WARN: The token is not a password *for* the bot. It **is** the bot. Anyone holding that string reads its messages and sends as it, no login required. Lives in `~/.openclaw/.env` — never a repo, never a screenshot.

## Stand it up on this box

<!--steps-->
1. **Token into the config** — `~/.openclaw/telegram-bridge.json`
2. **Allowlist yourself** — the `allowlist` array holds chat ids that may talk to it. Empty or wrong = the bot ignores you and looks broken.
3. **Point it at the right portal** — `portal` is the local service the bridge forwards to. Ember = `127.0.0.1:8088`. A new agent gets its OWN port (8092+).
4. **Lock the file down** — `chmod 600 ~/.openclaw/telegram-bridge.json`
5. **Restart the bridge** — `systemctl --user restart ember-telegram`. A new agent gets its own unit; don't hijack Ember's.
6. **Prove it's alive** — `curl .../bot<TOKEN>/getMe`, then message it. No reply = check the unit's logs, not the token.

> NOTE: One bot, one agent, one unit. Two agents sharing a token fight over `getUpdates` and each eat half the messages. It looks like packet loss. It is not.

## Rotate a token

`/mybots` → pick bot → **API Token** → **Revoke current token**. Revocation is **instant** — the old token dies the moment you tap.

> WARN: **The deaf-bot trap.** The bridge goes deaf the instant you revoke and stays deaf until the new token is in the config *and* the service is restarted. Do it when you have two minutes. Not at 1am on the way to bed.

## Knobs worth turning

All under `/mybots → <bot> → Bot Settings`.

| knob | what it does |
|---|---|
| Group Privacy | ON by default: bot sees only @mentions and replies |
| Edit Commands | fills the `/` menu — one `command - description` per line |
| Edit Description | shown on an empty chat; `About` is the short bio |
| Edit Botpic | because a default avatar looks abandoned |

## The Ember stack

| unit | role | where |
|---|---|---|
| `ember-home` | the face (portal) | `127.0.0.1:8088` |
| `ember-brain` | RAG brain, 681 chunks | `127.0.0.1:8089` |
| `ember-telegram` | the bridge — interactive only | — |
| `ollama` | inference, `qwen3-16k:14b` | `127.0.0.1:11434` |

Three `systemd --user` units, autostart on boot (linger on).

## emberctl — short alias `ember`

| command | what it's for |
|---|---|
| `status` \| `st` | one-glance health. Start here, always. |
| `doctor` \| `dr` | diagnose when status looks wrong |
| `up` / `down` / `restart` | the whole stack |
| `wake` | nudge her awake without a full restart |
| `telegram on\|off` | mute the bridge *without* taking her down |
| `chat <msg>` | talk to her from the terminal |
| `brain <q>` \| `ask` | query the RAG brain directly |
| `logs [home\|brain\|tg]` | per-service logs |
| `inbox` \| `mail` | anything waiting for her |

## Rotating Ember's token

The deaf window opens at step 2 and closes at step 4.

<!--steps-->
1. `ember telegram off` — close the bridge first, on your terms
2. `/mybots → Ember → API Token → Revoke` — **she is now deaf**
3. edit `~/.openclaw/telegram-bridge.json` — new token, keep allowlist `8331308861`
4. `ember telegram on` — **hearing restored**
5. `curl .../bot<TOKEN>/getMe` — prove it, don't assume

> WARN: **Live ammunition.** `telegram-bridge.json` still carries the token copied off the June-12 USB. It has never been rotated. All three units are ACTIVE as of this printing — a rotation interrupts a live agent.

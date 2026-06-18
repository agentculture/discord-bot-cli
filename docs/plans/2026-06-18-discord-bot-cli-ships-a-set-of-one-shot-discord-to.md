# Build Plan — discord-bot-cli ships a set of one-shot Discord tool verbs — read messages, post a message, react, reply, create a thread, post to a thread, list channels, list messages, and get users — so an agent can drive a Discord bot from the command line

slug: `discord-bot-cli-ships-a-set-of-one-shot-discord-to` · status: `exported` · from frame: `discord-bot-cli-ships-a-set-of-one-shot-discord-to`

> discord-bot-cli ships a set of one-shot Discord tool verbs — read messages, post a message, react, reply, create a thread, post to a thread, list channels, list messages, and get users — so an agent can drive a Discord bot from the command line

## Tasks

### t1 — Transport seam discord_client.py: read DISCORD_BOT_TOKEN (else EXIT_ENV_ERROR+hint, never echo it), lazy-import discord.py (else EXIT_ENV_ERROR+install hint), async run(action) helper that logs in, awaits the action, always closes the client, and maps discord exceptions to CliError

- covers: h1, c12, h10
- acceptance:
  - missing DISCORD_BOT_TOKEN -> CliError exit 2 with a hint; the token value is never written to stdout/stderr
  - discord.py not installed -> CliError exit 2 with an install hint (uv add discord-bot-cli[discord]), not an ImportError traceback
  - run() logs in, awaits the action coroutine, and closes the client in a finally so no connection is left open; returns the action result
  - discord Forbidden/NotFound/HTTPException/LoginFailure are caught and re-raised as CliError; no traceback leaks

### t2 — Packaging + no-runtime-dep guard: add [project.optional-dependencies] discord = discord.py and add it to the dev group; add a static test asserting pyproject dependencies==[] and no discord_bot_cli module imports a third-party package at module top level

- covers: c4, h8
- acceptance:
  - pyproject [project].dependencies == []; discord.py appears only under optional-dependencies.discord and the dev dependency group
  - a test imports/AST-scans every discord_bot_cli module and asserts no top-level 'import discord' (lazy imports inside functions are allowed)

### t3 — channel noun (cli/_commands/channel.py): 'channel list <guild_id>' (guild's channels), 'channel messages <channel_id> --limit N' (last N), and 'channel overview'; identifiers are plain positional args, results emit --json

- depends on: t1
- covers: c2, h7
- acceptance:
  - channel list <guild_id> --json returns a JSON array of {id,name,type}; handler stubs the t1 seam in tests (no live token)
  - channel messages <channel_id> --limit N --json returns up to N messages; --limit is range-validated with a hint on bad input
  - channel overview exists and is reachable (rubric: a noun with verbs exposes overview)

### t4 — message noun (cli/_commands/message.py): 'message post <channel_id> <content>', 'message reply <channel_id> <message_id> <content>', 'message react <channel_id> <message_id> <emoji>', and 'message overview'; post/reply return the created message id so output composes into the next verb

- depends on: t1
- covers: c5, h9
- acceptance:
  - message post --json returns the created message id (and channel id) so it can feed reply/react
  - message reply attaches a message_reference to the target; message react adds the emoji; both stub the seam in tests
  - message overview exists and is reachable

### t5 — thread noun (cli/_commands/thread.py): 'thread create <channel_id> --name <name> [--message <message_id>]' (message-anchored or standalone), 'thread post <thread_id> <content>', and 'thread overview'; each verb is a single non-interactive invocation

- depends on: t1
- covers: c3, h2
- acceptance:
  - thread create --json returns the new thread id; supports both a message-anchored thread and a standalone thread
  - thread post sends a message to the thread; every verb handler returns an int exit code (0 on success)
  - thread overview exists and is reachable

### t6 — user noun (cli/_commands/user.py): 'user get <user_id>' and 'user overview'; returns a machine-parseable user record

- depends on: t1
- acceptance:
  - user get <user_id> --json returns {id,username,global_name,bot}; stubs the seam in tests
  - user overview exists and is reachable

### t7 — Wiring + discoverability: register the four nouns in cli/__init__.py:_build_parser(); add an explain/catalog.py entry for every new command path tuple; surface the new verbs in the hand-maintained learn.py (_TEXT and _as_json_payload) and overview.py (_VERBS) lists

- depends on: t3, t4, t5, t6
- covers: c1
- acceptance:
  - every new command path resolves via explain (test_every_catalog_path_resolves passes for the new tuples)
  - learn and overview list the new nouns/verbs; 'teken cli doctor . --strict' (the afi rubric gate) passes including overview-exists for each new noun

### t8 — Integration test + docs alignment: an end-to-end test stubbing the t1 seam that walks channel list -> channel messages -> message post -> reply -> react -> thread create -> thread post -> user get, asserting each verb invokes the expected discord.py method; update README.md (verb usage + DISCORD_BOT_TOKEN + [discord] extra) and CLAUDE.md (the discord_client seam + new nouns)

- depends on: t7
- covers: c7, h3
- acceptance:
  - the integration test stubs the seam (no live token) and asserts each verb maps to its documented discord.py / REST endpoint call
  - README documents each verb with the DISCORD_BOT_TOKEN env var and the [discord] install extra; CLAUDE.md describes the discord_client seam and the four new nouns (doc-test alignment)

## Risks

- [unknown_nonblocking] discord.py REST-only path: verbs assume Client.login()+fetch_*/send/add_reaction/create_thread work WITHOUT a persistent gateway connect(); if any operation needs the gateway or a privileged intent, the seam (t1) must adapt. To be de-risked via ask-colleague explore before t3-t6 land. (task t1)

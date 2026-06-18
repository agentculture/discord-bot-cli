# discord-bot-cli ships a set of one-shot Discord tool verbs — read messages, post a message, react, reply, create a thread, post to a thread, list channels, list messages, and get users — so an agent can drive a Discord bot from the command line

> discord-bot-cli ships a set of one-shot Discord tool verbs — read messages, post a message, react, reply, create a thread, post to a thread, list channels, list messages, and get users — so an agent can drive a Discord bot from the command line

## Audience

- an AI agent (and its human operator) that needs to read and act in Discord via a bot, driven from the discord-bot-cli command line

## Before → After

- Before: the Discord domain is unimplemented; discord-bot-cli is only the introspection scaffold (whoami/learn/explain/overview/doctor) with zero runtime dependencies
- After: the agent can run discrete verbs — channel list/messages, message post/reply/react, thread create/post, user get/list — each emitting agent-first stdout/stderr + --json, with no long-running daemon

## Why it matters

- this is the repo's stated reason to exist — giving an agent Discord access via a bot — and one-shot verbs compose into agent loops and mesh workflows the way the other AgentCulture CLIs do

## Honesty conditions

- every listed verb works end-to-end against the real Discord REST API v10 with a bot token, returning structured --json and routing failures through the CliError contract (no traceback)
- the verbs are usable by an agent with no Discord-library knowledge: identifiers (channel/message/user IDs) are passed as plain args and results are machine-parseable via --json
- each verb is a single non-interactive invocation that exits 0 on success and a documented non-zero code on failure; no verb starts a persistent process
- before this lands, the package exposes no Discord capability (a git grep for the verb names in discord_bot_cli/ returns nothing) so the increment is additive over the scaffold
- each verb is independently invocable and composes in a shell/agent loop (output of one verb, e.g. a posted message id, can feed the next), matching how the other AgentCulture CLIs are driven
- the channel/message/thread/user verbs each map to a documented Discord REST endpoint and are covered by tests that stub the HTTP layer (no live token needed in CI)
- the token is read from DISCORD_BOT_TOKEN; absence raises EXIT_ENV_ERROR(2) with a hint, and the token value is never echoed to stdout/stderr or logs
- no verb leaves a process running after it prints its result; a test asserts each handler returns an int exit code and does not block
- discord.py is imported only inside command handlers (a static test asserts no top-level third-party import in the package); pyproject keeps dependencies=[] with discord.py solely under optional-dependencies + the dev group, and the absent-extra path returns EXIT_ENV_ERROR(2) not a traceback

## Success signals

- an agent can, with a bot token, list a guild's channels, read the last N messages of a channel, post a message, reply, react, create+post to a thread, and look up a user — each as a single CLI invocation with structured --json output and the agent-first error contract

## Scope / boundaries

- not a persistent gateway listener and not a daemon: each verb connects via the library, performs one action, and exits; no slash-command registration, no voice, no event subscriptions this increment

## Non-goals

- no message-content caching/database, no rate-limit queueing beyond honoring 429 retry-after, no media/attachment upload in this increment

## Assumptions

- auth is a Discord bot token supplied via env var (DISCORD_BOT_TOKEN), never a flag, and missing/invalid token yields EXIT_ENV_ERROR(2) with a hint — no OAuth, no user tokens

## Decisions

- verbs are grouped under nouns matching Discord's REST resources: 'channel' (list/messages), 'message' (post/reply/react), 'thread' (create/post), 'user' (get); each noun exposes 'overview' per the agent-first rubric
- transport uses the official discord.py library declared as an optional [discord] extra (also in the dev group so CI tests it), lazy-imported inside verb handlers like ec2-cli's boto3 and reterminal's Pillow; pyproject runtime dependencies stay [] and a verb run without the extra raises EXIT_ENV_ERROR(2) with an install hint

## Open / follow-up

- pagination strategy for list messages beyond a single --limit (before/after cursors)

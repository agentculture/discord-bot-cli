# Attachments + analysis-grade reads

> discord-bot-cli 0.6.0 ships file attachments on the write verbs and the read fields a statistics pipeline needs: 'message post/reply' and 'thread post' take a repeatable --file, and 'channel messages' can page a real time window while 'user get' resolves a batch of ids in one session (always emitting a JSON array — a breaking change to the single-id output shape, hence the minor bump from 0.5.0).
> instruction: Ship behind the existing lanes: stubbed tests through the `discord_client`.run seam for every verb/flag mapping, the gated live lane (`DISCORD_LIVE_TESTS`=1, sandbox #spark-tests) for the two things a stub cannot prove — a real multipart upload and real paging past 100 — plus a version bump per PR (version-check CI blocks otherwise) and the three hand-maintained prose lists updated.

## Audience

- Consumer CLIs and mesh agents that use discord-bot-cli as a transport: sensibo-cli (posting rendered chart reports) and jetson-ai-lab-cli (a read-only participation-statistics report over ~134 Jetson AI Lab channels), plus any future agent that wants to attach a file or scan a channel.

## Before → After

- Before: 'message post' and 'message reply' only send text (message.py:34-45 calls channel.send(args.content) with no file= argument); sensibo-cli worked around it with ~30 lines of urllib multipart against a raw Discord webhook URL, bypassing this CLI's error contract and --json entirely.
- Before: 'channel messages' has `_LIMIT_MAX` = 100 and only --limit, so a time window is unexpressible and a busy channel silently truncates — the caller cannot distinguish hitting the cap from reaching the end of the window.
- Before: `_message_dict`() serialises only author.id and author.name — no 'bot' flag and no '`global_name`' — even though 'user get' already returns both, so the field is exposed on one noun and not the other.
- Before: 'user get' takes exactly one id per invocation, each its own process and REST round trip; resolving a few hundred ids is the bottleneck in an otherwise fast channel scan.
- After: An agent posts a rendered report image to Discord with a single 'message post <channel> "caption" --file chart.svg' call, through this CLI's CliError contract and --json payload, instead of hand-rolling a multipart/form-data webhook POST.
- After: A read-only scan can express a time window ('the last 90 days'), pages past the 100-message REST cap, and can tell from --json whether the requested window was fully covered rather than silently truncated.
- After: A statistics pipeline keyed on author.id can exclude bots and render human-recognisable names straight from 'channel messages --json', without a second round trip per author.
- After: Resolving several hundred user ids costs one process and one Discord login instead of one per id, and a single unresolvable id yields an error entry rather than failing the batch.

## Why it matters

- Every consumer that hits these gaps re-implements a seam that belongs in the transport CLI — two sibling repos already carry local workarounds (sensibo-cli's webhook multipart; jetson-ai-lab-cli reaching into raw discord.py objects inside action closures). Each workaround is a second implementation of this repo's job and escapes its error/JSON contract.

## Requirements

- 'message post', 'message reply' and 'thread post' accept a repeatable, order-preserving --file PATH; the positional content becomes optional once at least one --file is given (an attachment-only message is valid on Discord).
  - instruction: Build discord.File objects in the action closure and pass files= to channel.send / target.reply / thread.send. Make 'content' nargs='?' with default None and reject the both-empty case as `EXIT_USER_ERROR`. Test via the stubbed `discord_client`.run seam (tests/conftest.py FakeChannel.send must grow a files= kwarg it records).
  - honesty: The installed discord.py exposes send(files=\[discord.File(...)\]) and reply(files=...) on every Messageable we use (TextChannel, Thread, Message.reply) — verified against the version pinned by the \[discord\] extra, not assumed from docs.
  - honesty: Making 'content' optional does not break the existing positional form: 'message post <channel> <text>' and 'message post <channel> --file a.png' and 'message post <channel> <text> --file a.png' all parse under argparse's nargs='?'.
- Attachment failures route through the CliError contract: an unreadable or missing path fails before login, more than 10 files is rejected client-side, and a Discord 413 (size) is mapped to a typed error naming the size sent — each exits 1 with a remediation and no traceback reaches stderr.
  - instruction: Per the q2 decision: no size pre-flight — os.stat only to prove the path is readable, never to guess a limit. The 10-attachment count IS asserted client-side (fixed documented Discord limit). The size case is discord.HTTPException status 413 mapped in `discord_client`.run's existing handler chain, with the byte count we sent in the message. Assert exit code and the 'error:'/'hint:' stderr shape in tests, not just the message text.
  - honesty: The 10-attachment cap is a fixed, documented Discord limit we can assert client-side; the per-file size cap is guild-tier dependent and therefore cannot be named accurately without knowing the guild.
  - honesty: Mapping the 413 requires that discord.py surfaces an oversized upload as an HTTPException with status 413 (not a lower-level connection error mid-upload), so the existing handler chain in `discord_client`.run can name it.
- --json on post/reply/thread-post includes the resulting attachment ids and URLs alongside the message id, so a caller can reference what it uploaded.
  - instruction: Read message.attachments from the discord.py return value; each entry {id, filename, url, size}. Extend the conftest FakeMessage to carry attachments.
  - honesty: message.attachments is populated on the object returned by send()/reply() — i.e. Discord echoes the attachment metadata back on the create response, so no extra fetch is needed to report ids and URLs.
- 'channel messages' gains a time-window option (--after/--since) that pages past the 100-message cap, and its --json payload carries an explicit signal for whether the requested window was fully covered.
  - instruction: Per the q3 decision: --since accepts an ISO 8601 timestamp, a partial timestamp (date-only '2026-06-01' = midnight UTC that day), or a relative duration ('90d'); durations resolve CLI-side to now - delta. discord.py's history(after=) takes a datetime and supports limit=None for paging. Keep --limit's 1-100 validation for the no-window case; when a window is given, page and report coverage. The coverage signal must be present on every --json run, not only on truncation, so callers can assert on it unconditionally.
  - honesty: Paging with after= and limit=None is bounded in practice: a 90-day window on the busiest Jetson AI Lab channel completes in acceptable time and API budget, or the verb carries an explicit cap that surfaces as the coverage signal rather than running unbounded.
  - honesty: The coverage signal answers the question a caller actually has — 'did I see every message in the window' — and is not merely 'did I hit --limit'.
- `_message_dict`() gains author.bot and author.`global_name`, matching the fields 'user get' already returns.
  - instruction: Use getattr with None/False defaults exactly as the existing fields do, so the stubbed FakeUser and a real discord.py Member both work. Update the human (non-JSON) renderer only if it stays one line per message.
  - honesty: Adding author.bot and author.`global_name` to `_message_dict`() is purely additive: no existing key is renamed or removed, so current consumers (including the human renderer's author.name) keep working.
  - honesty: A per-guild nick is only available when the message author is a guild Member; over channel.history() with Intents.none() and no member cache the author may be a plain User, so nick cannot be promised unconditionally.
- 'user get' takes one or more ids (varargs, plus --ids-file with '-' for stdin), resolves them all inside one `discord_client`.run() session, and always emits a JSON array — including for a single id. Resolution is tolerant per id: an unresolvable id yields an error entry instead of failing the batch.
  - instruction: Per the q1/v1 decisions: always-array is a BREAKING change to the current single-id object output — it needs a minor bump and an explicit CHANGELOG entry, and the explain/learn/overview prose must state it. Keep it one asyncio.run/login (the one-shot contract is about not leaving a daemon running, not about one REST call). Catch per-id NotFound/Forbidden inside the loop and record {id, error, remediation} rather than raising out of the action.
  - honesty: One login can carry hundreds of `fetch_user` calls without tripping Discord's rate limits in a way that makes the batch slower or less reliable than the per-process form — discord.py's internal rate-limit handling is sufficient here.
- The self-teaching surfaces stay true: explain/catalog.py entries, learn.py (`_TEXT` and `_as_json_payload`) and overview.py (`_VERBS`) all describe the new flags.
  - instruction: These three lists are hand-maintained (no generation from the catalog) — CLAUDE.md 'Adding a command' step 4. `test_every_catalog_path_resolves` and the teken rubric gate cover the catalog but not the prose, so the prose has to be read.
  - honesty: The three lists are genuinely un-generated from one another: catalog ENTRIES, learn.py's `_TEXT`/`_as_json_payload`, and overview.py's `_VERBS` are each independently authored, so no test catches prose that describes the old surface.

## Honesty conditions

- Both filing consumers can actually drop their workarounds on this surface — sensibo-cli's chart delivery and jetson-ai-lab-cli's participation scan each work end to end against the shipped flags, not just against our stubbed tests.
- The increment holds the repo's two hard constraints unchanged: dependencies = \[\] (`test_no_runtime_deps.py` untouched) and one-shot no-daemon transport.
- The audience is real and named, not hypothetical: issues #13 and #14 were filed by those two consumer agents against this repo, each describing a concrete blocked or degraded workflow — not a speculative 'someone might want this'.
- 'One call' is literally true end to end: a single 'message post <channel> "caption" --file chart.svg' invocation uploads and posts, with no companion webhook step, no pre-upload to a host, and no second command to attach.
- 'Pages past the cap' means the caller actually receives every message in the window, not just a larger page — a 90-day window over a channel with 500 messages returns 500, and the coverage signal says so.
- 'Without a second round trip' holds for both fields: bot and `global_name` come from the author object discord.py already attaches to each history message, so no extra `fetch_user` call is issued per author.
- 'One login' is observably true, not just architecturally intended: a batch of N ids results in exactly one discord.Client login and one close, assertable by counting calls against the stubbed seam.
- The gap is real and not an undocumented flag: 'message post --help' shows no file option, and a grep for attachment/multipart/files/upload across the package returns nothing — both checks the issue reporter ran and this scope pass re-ran against message.py.
- The truncation is genuinely silent: nothing in the current --json payload or exit code tells a caller that --limit 100 was a ceiling rather than the end of the channel's history.
- The asymmetry is exactly as described: 'user get' returns both bot and `global_name` today (user.py), while `_message_dict`() (channel.py) returns neither — so this is closing an inconsistency inside one CLI, not adding a novel field.
- The cost is per-invocation, not merely per-request: each 'user get' is a separate OS process AND a separate Discord login handshake, so the overhead a batch form removes is real rather than a micro-optimisation of one HTTP call.
- Both workarounds actually exist in the sibling repos as described — sensibo-cli's urllib multipart webhook post and jetson-ai-lab-cli's reuse of `discord_client`.run() with raw discord.py objects — rather than being hypothetical duplication we are arguing against.
- The constraint holds under test, not just by inspection: tests/`test_no_runtime_deps.py` continues to pass unmodified, proving both dependencies == \[\] and no top-level third-party import anywhere in the package.
- Batch resolution genuinely does not weaken the contract: no gateway subscription is opened, Intents.none() is unchanged, and the client is still closed in the finally, so nothing survives the process.
- The claim is verified by the consumer, not by us: sensibo-cli reports its workaround deleted after adopting the flag. If it adopts and keeps the webhook path for an unrelated reason, this signal is not met and must not be reported as met.
- '0 local re-implementations' is checked against jetson-ai-lab-cli's actual code after adoption, and the paging half is proven on a real channel with more than 100 messages in the window — a stubbed test cannot establish it.
- The 200:1 ratio is the real invocation count from the consumer's call site, not a theoretical maximum — i.e. the consumer genuinely batches rather than looping the batch form one id at a time.

## Success signals

- sensibo-cli deletes its ~30-line urllib multipart webhook workaround and posts chart reports through 'message post --file' — a net removal of roughly 30 lines in the consumer, with 0 lines of transport code left there.
  - instruction: Confirm by asking sensibo-cli (via the communicate skill) to report the diff after adopting it; the signal is the workaround's deletion, not our tests passing.
- jetson-ai-lab-cli's participation report runs with 0 local re-implementations of these 4 seams, and a 90-day scan of a busy channel emits its coverage signal rather than silently returning exactly 100 messages.
  - instruction: Verify against the real guild in the live-test lane (`DISCORD_LIVE_TESTS`=1) on a channel with more than 100 messages in the window, since the stubbed seam cannot prove paging against real REST.
- Resolving 200 user ids goes from 200 CLI invocations and 200 logins to 1 invocation and 1 login.
  - instruction: Countable from the consumer's call site; assert the single-session property in a stub test by counting `discord_client`.run invocations.

## Scope / boundaries

- Zero runtime dependencies is unchanged: discord.File and everything else new stays behind `discord_client`.`require_discord`()'s lazy import under the \[discord\] extra. tests/`test_no_runtime_deps.py` still passes untouched.
- The one-shot, no-daemon contract holds. Batch id resolution is one login and one session, not a resident client or a gateway subscription; Intents.none() stays.

## Non-goals

- No new write paths for the statistics work — all four asks in #14 are read-only. No delete verb, no edit verb, no attachment download/retrieval verb.
- No 'guild' noun in this increment (still parked from the previous frame), and no rate-limit orchestration beyond what discord.py already does.

## Assumptions

- The two issues are independent and could ship as separate PRs; scoping them together is a convenience, not a coupling.

## Scope exploration

- `s1` — `discord_bot_cli/cli/_commands/message.py`: `cmd_message_post`/reply build an async action and call channel.send(args.content) / target.reply(args.content) — no files= argument anywhere, and 'content' is a required positional. Adding attachments is argparse plumbing plus discord.File construction inside the existing action closure; no new transport code.
  - seeds: `c7`, `c12`, `c14`
- `s2` — `discord_bot_cli/cli/_commands/thread.py`: `cmd_thread_post` has the identical shape (thread.send(args.content)), so it is a third site that must grow --file for consistency — the issue calls this out and the all-verbs symmetry argument applies.
  - seeds: `c12`
- `s3` — `discord_bot_cli/cli/_commands/channel.py`: `_LIMIT_MIN`/`_LIMIT_MAX`/`_LIMIT_DEFAULT` = 1/100/20 with a CliError on out-of-range; the action does \[m async for m in channel.history(limit=args.limit)\] then reverses. `_message_dict`() emits only author.{id,name}, content, `created_at`. Both gaps in #14 (1-3) live in this one file.
  - seeds: `c8`, `c9`, `c15`, `c16`
- `s4` — `discord_bot_cli/cli/_commands/user.py`: `cmd_user_get` parses exactly one id, and its action does a single await client.`fetch_user`(`user_id`) returning {id, username, `global_name`, bot} — so 'user get' already exposes the two fields `_message_dict` lacks, and batching is a loop inside the same action, not a new seam.
  - seeds: `c10`, `c17`
- `s5` — `discord_bot_cli/discord_client.py`: run() is the single transport seam: `require_token` (env only) -> `require_discord` (lazy import, keeps dependencies = \[\]) -> asyncio.run(login -> action -> always close), with LoginFailure/Forbidden/NotFound/HTTPException/DiscordException each mapped to CliError. Batch resolution fits the contract (one login, one session); per-id tolerance means catching NotFound/Forbidden inside the action rather than letting run() map them.
  - seeds: `c19`, `c20`, `c13`
- `s6` — `tests/conftest.py (the stubbed seam)`: FakeChannel/FakeMessage/FakeThread/FakeUser record calls and FakeChannel.send/FakeMessage.reply take content only — every new kwarg (files=, after=, limit=None) needs the fake widened, and FakeMessage has no .attachments, so the --json attachment payload cannot be asserted until it does. The stub cannot prove real paging or a real multipart upload; only the gated live lane can.
  - seeds: `c12`, `c14`, `c15`
- `s7` — `explain/catalog.py + learn.py + overview.py (self-teaching surfaces)`: Three hand-maintained lists: catalog ENTRIES keyed by path tuple (already has every channel/message/thread/user path), learn.py's `_TEXT` and `_as_json_payload`, and overview.py's `_VERBS`. None is generated from another, so a new flag is documented in three places or the CLI teaches the next agent something false.
  - seeds: `c18`
- `s8` — `GitHub issues #13 (sensibo-cli) and #14 (jetson-ai-lab-cli)`: Both filed by sibling mesh agents with working local workarounds, so neither is blocking. #13 asks for one thing (attachments); #14 asks for four, of which its author flags (1) time-window paging and (4) batch id resolution as the valuable ones — (2) author.bot and (3) `global_name` are cheap field additions to the same dict.
  - seeds: `c2`, `c11`
- `s9` — `the previous devague frame (discord-bot-cli-ships-a-set-of-one-shot-discord-to)`: Its still-open parked item reads 'pagination strategy for list messages beyond a single --limit (before/after cursors)' — the exact gap #14 item 1 now reports from a real consumer. This increment is the decision that frame deferred, so the paging design is a resolution of prior parked vagueness, not a new idea.
  - seeds: `c15`

## Hard questions

- risk: The live-test lane posts for real and there is still no delete verb, so attachment write tests permanently litter the sandbox channel (#spark-tests) with files.
- What size limit does the pre-flight check enforce, given the real cap depends on the guild's boost tier? Options: hard-code the 8 MiB unboosted floor (rejects valid uploads on boosted guilds), fetch the guild to read its tier (an extra round trip and a guild id the message verbs do not currently take), or skip the pre-flight and map Discord's 413 cleanly. (resolved: USER: no size pre-flight. Only Discord knows the guild's real cap, so upload and map the HTTP 413 into a CliError naming the size sent and Discord's own message. The 10-attachment count cap is still asserted client-side (it is a fixed documented limit); the size cap is not guessed.)
- What does --after/--since accept: an ISO 8601 timestamp, a relative duration like '90d', or a message-id snowflake? discord.py's history(after=) takes a datetime or a Snowflake-ish object; the CLI has to pick a surface and say so. (resolved: USER: accept both an ISO 8601 timestamp and a relative duration ('90d'), and accept a partial timestamp — a date-only '2026-06-01' is valid and means midnight UTC that day. Durations are resolved CLI-side to now - delta and handed to discord.py's history(after=<datetime>).)
- risk: 'channel messages' currently validates --limit into \[1,100\]. Once paging exists, that ceiling means two different things depending on whether a window was given — a subtle contract change worth stating explicitly rather than leaving implicit.
- Does the batch form change the output shape of the existing single-id 'user get <id> --json' (object) into an array? That is a backward-compatibility break for any current consumer; the alternative is emitting an object for one id and an array for many, which is worse to parse. (resolved: USER: always an array. 'user get <id> --json' emits a 1-element array too — one shape for consumers to parse. This is a breaking change to the current single-id object contract, so it takes a minor version bump and an explicit CHANGELOG entry.)

## Open parks

- [unknown_nonblocking] Whether --before (the closing edge of the window) is in scope this increment, or only the opening edge --after/--since.
- [unknown_nonblocking] Whether to include the per-guild nick at all in this increment, given it needs a Member object the history path may not have (see h7).
- [follow_up] Whether this ships as one PR or two: #13 (attachments, write path) and #14 (analysis-grade reads) touch disjoint files and have independent consumers, but each PR needs its own version bump under the version-check CI job.
- [follow_up] Whether the hand-maintained learn/overview/catalog lists should eventually be generated from one source, since this is the second increment that has to update three prose lists by hand.

## Resolved vagueness

- [unknown_blocking] How ids arrive in the batch form: positional varargs ('user get <id> <id> ...'), an --ids-file, or newline-delimited stdin. The issue offers all three; varargs collides with nothing today but caps out at `ARG_MAX` for very large scans. — resolved: USER: varargs plus --ids-file. 'user get 1 2 3' for a handful; '--ids-file ids.txt' (newline-delimited, '-' meaning stdin) for a scan, so a few-hundred-id resolve is not bounded by `ARG_MAX`.

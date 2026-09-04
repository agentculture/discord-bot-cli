# Build Plan — Attachments + analysis-grade reads

slug: `attachments-analysis-grade-reads` · status: `exported` · from frame: `attachments-analysis-grade-reads`

> discord-bot-cli 0.6.0 ships file attachments on the write verbs and the read fields a statistics pipeline needs: 'message post/reply' and 'thread post' take a repeatable --file, and 'channel messages' can page a real time window while 'user get' resolves a batch of ids in one session (always emitting a JSON array — a breaking change to the single-id output shape, hence the minor bump from 0.5.0).

## Tasks

### t1 — Widen tests/conftest.py fakes for every new surface

- instruction: Touches tests/conftest.py ONLY. Every other task in this plan depends on it, so it is the wave-1 serializer — landing it alone keeps later waves file-disjoint. Widening must be strictly additive: the 61 existing tests pass without edits.
- acceptance:
  - FakeChannel.send and FakeMessage.reply record a files= kwarg and still accept content-only calls, so existing tests pass unchanged
  - FakeMessage exposes .attachments with id/filename/url/size entries
  - FakeChannel.history accepts after=, limit=None and `oldest_first`=, and yields in the order those arguments imply rather than a fixed order
  - FakeClient.`fetch_user` can be told to raise NotFound/Forbidden for specific ids, so per-id batch tolerance is testable

### t2 — Add `discord_bot_cli`/cli/`_commands`/`_attachments.py` — the shared --file seam

- instruction: New file, disjoint from every existing module. Verified against discord.py 2.7.1: File.`__init__` opens fp eagerly (OSError), send() raises ValueError for an over-long files list and TypeError on file/files conflicts — none are discord.\* subclasses, so `discord_client`.run's handler chain does not map them. That is why the guard lives here, ahead of the transport.
- depends on: t1
- covers: c12, h1, h2, c13, h9, h10, c14, h3, c29, h31, c19, h24
- acceptance:
  - `add_file_flag`(parser) registers a repeatable, order-preserving --file and makes the content positional nargs='?'
  - `build_files`(paths) returns discord.File objects in argument order, importing discord lazily via `discord_client`.`require_discord`()
  - a missing, unreadable, or directory path raises CliError(`EXIT_USER_ERROR`) with a remediation before any login happens — OSError never escapes
  - an 11th path raises CliError naming the 10-attachment Discord limit, so discord.py's own ValueError is never the path a user sees
  - content=None with zero files raises CliError; content=None with >=1 file is accepted
  - `attachments_payload`(message) maps message.attachments to \[{id, filename, url, size}\]
  - tests/`test_no_runtime_deps.py` passes unmodified, proving the new module has no top-level third-party import

### t3 — Add `discord_bot_cli`/cli/`_commands`/`_timewindow.py` — parse --since into an aware UTC datetime

- instruction: New file, disjoint. This exists as its own module precisely because discord.py 2.7.1 documents 'if the datetime is naive, it is assumed to be local time' — the aware-UTC guarantee is the whole point, and it needs its own test file to prove the TZ independence.
- depends on: t1
- covers: c28, h30
- acceptance:
  - an ISO 8601 timestamp with an offset parses to the equivalent UTC instant
  - a date-only '2026-06-01' parses to 2026-06-01T00:00:00+00:00 — midnight UTC, per the q3 decision
  - a duration '90d' (and h/w/m forms) resolves to now - delta as an aware UTC datetime
  - the returned datetime is ALWAYS tz-aware; a naive value can never be returned
  - the same input under TZ=America/`New_York` and TZ=UTC produces an identical instant — the test forces TZ, it does not rely on CI being UTC
  - garbage input raises CliError(`EXIT_USER_ERROR`) with a hint naming the three accepted forms

### t4 — Wire --file into message post and message reply

- instruction: Touches `discord_bot_cli`/cli/`_commands`/message.py and tests/`test_discord_message.py` only. All plumbing comes from `_attachments.py` — this task adds no error handling of its own. Name the --json attachment field so it cannot be read as durable storage (c33: the URL 404s once the message is deleted).
- depends on: t1, t2
- covers: c3, h14, c7, h18, c33, h35
- acceptance:
  - message post <channel> <content> --file a.png --file b.png sends ONE message carrying both files, in that order
  - message post <channel> --file a.png (no content) succeeds
  - message post <channel> <text>, --file-only, and both-together all parse — the existing positional form is not broken by nargs='?'
  - message reply accepts --file with identical semantics
  - --json output includes the attachment ids and URLs alongside the message id
  - no companion webhook call or second command is issued: one invocation, one send

### t5 — Wire --file into thread post

- instruction: Touches `discord_bot_cli`/cli/`_commands`/thread.py and tests/`test_discord_thread.py` only — file-disjoint from t4, so the two run in the same wave. The payload shape must match message post's byte for byte; a consumer should not need to branch on which verb produced it.
- depends on: t1, t2
- covers: c12
- acceptance:
  - thread post <`thread_id`> <content> --file a.png attaches the file to the message posted in the thread
  - thread post <`thread_id`> --file a.png (no content) succeeds
  - --json includes the attachment ids and URLs, matching message post's payload shape exactly

### t6 — Add the --since time window and coverage signal to channel messages

- instruction: Touches `discord_bot_cli`/cli/`_commands`/channel.py and tests/`test_discord_channel.py`. THE TRAP (c27): discord.py 2.7.1 sets `oldest_first`=True by default when after= is given, so the existing unconditional collected.reverse() inverts a windowed read. Pass `oldest_first` explicitly or normalise after collection — and test both paths, because the current single-path coverage would let this ship green.
- depends on: t1, t3
- covers: c15, h4, h5, c27, h29, c4, h15, c8, h19
- acceptance:
  - --since pages past the 100-message cap: a window over a channel with 250 messages returns all 250
  - output is oldest-first for BOTH a windowed read and a plain --limit read — the windowed path is asserted explicitly, not assumed
  - --limit alongside --since caps the walk; --json then reports the window as not fully covered and names what stopped it (limit vs window end)
  - the coverage signal is present on EVERY --json run, including fully-covered and non-windowed ones, so callers can assert on it unconditionally
  - --limit without --since keeps its existing 1-100 validation and CliError

### t7 — Give user get a batch form

- instruction: Touches `discord_bot_cli`/cli/`_commands`/user.py and tests/`test_discord_user.py` only. Per q6: exit 0 even when some ids fail. Per q8: input order is a documented guarantee, so do not parallelise resolution without a reordering buffer. Catch NotFound/Forbidden INSIDE the action loop — letting them reach `discord_client`.run would fail the whole batch.
- depends on: t1
- covers: c17, h8, c6, h17, c10, h21, c20, h25
- acceptance:
  - user get <id> <id> <id> resolves all three inside ONE `discord_client`.run session — assertable by counting run/login invocations
  - user get --ids-file ids.txt reads newline-delimited ids; --ids-file - reads them from stdin
  - --json ALWAYS emits an array, including for a single id
  - an unresolvable id yields an {id, error, remediation} entry and the process still exits 0 — the other ids still resolve
  - output order matches input order, for both --json and the human renderer
  - the human renderer emits one line per user, errors on their own line

### t8 — Add author.bot and author.`global_name` to `_message_dict`()

- instruction: Touches `discord_bot_cli`/cli/`_commands`/channel.py — the SAME file as t6, which is why it depends on t6 rather than sharing its wave. The dependency is purely for file disjointness, not content. Do NOT promise a per-guild nick: over channel.history() with Intents.none() the author may be a plain User, not a Member (h7).
- depends on: t6
- covers: c16, h6, h7, c5, h16, c9, h20
- acceptance:
  - channel messages --json returns author.bot and author.`global_name` for every message
  - no existing key is renamed or removed; the human renderer's author.name output is byte-identical to before
  - neither field costs an extra `fetch_user` call — assertable by counting client calls against the fake
  - a stubbed FakeUser without `global_name` yields None rather than raising, matching the getattr defaults the module already uses

### t9 — Map the Discord 413 into the CLI error contract

- instruction: Touches `discord_bot_cli`/`discord_client.py` and tests/`test_discord_client.py`. Per the q2 decision there is NO size pre-flight: only Discord knows the guild's real cap, so this is the whole size story. Slot the 413 case ahead of the generic HTTPException handler in the existing chain.
- depends on: t2
- covers: h10
- acceptance:
  - an HTTPException with status 413 raised during a send becomes a CliError naming the byte size that was sent and Discord's own message
  - the remediation names the boost-tier dependence rather than asserting a fixed limit
  - exit code is 1 and stderr carries the error:/hint: shape — asserted on the streams, not just the message text

### t10 — Update the three hand-maintained self-teaching surfaces

- instruction: Touches explain/catalog.py, cli/`_commands`/learn.py and cli/`_commands`/overview.py. These three lists are hand-maintained and un-generated (CLAUDE.md 'Adding a command' step 4), so no test catches stale prose — the prose has to be read. Boundary c31 must land HERE, in what the next agent actually reads before using the flag, not only in the spec.
- depends on: t4, t5, t6, t7, t8
- covers: c18, h23, c31, h33, c33
- acceptance:
  - explain/catalog.py documents --file on message post/reply and thread post, --since and the coverage signal on channel messages, and the batch + always-array shape on user get
  - learn.py `_TEXT` and `_as_json_payload` both list the new flags — the JSON payload is not left behind the prose
  - overview.py `_VERBS` shows the new signatures
  - the catalog states that --file is an unsandboxed local read and that an attachment URL is a reference, not storage
  - the catalog states that user get --json always emits an array, and that this changed in 0.6.0
  - `test_every_catalog_path_resolves` still passes

### t11 — Add the live-lane tests only a real Discord can prove

- instruction: Touches tests/`test_live_discord.py` and the live-test prose in CLAUDE.md/README. Per memory: sandbox is #spark-tests in the JetsonBot experiments guild; #pull-requests blocks the bot. The paging test needs a channel with >100 messages inside the window or it proves nothing.
- depends on: t4, t6
- covers: c32, h34, c25, h27
- acceptance:
  - a gated live test uploads a real file via message post --file and asserts the returned attachment id and URL
  - a gated live test pages a window with more than 100 messages and asserts full coverage — the stub cannot establish this
  - both stay doubly gated: they self-skip unless `DISCORD_LIVE_TESTS`=1 and `DISCORD_BOT_TOKEN` are both set, so a routine pytest run never uploads
  - the docs state that these tests leave permanent artifacts and must point at the sandbox channel, since no delete verb exists

### t12 — Release 0.6.0: version, CHANGELOG, README

- instruction: Touches pyproject.toml, CHANGELOG.md, README.md. Use the version-bump skill (minor — the breaking user get shape is what forces it above a patch). `__version__` reads from installed metadata, so re-run uv sync or whoami will report the old number.
- depends on: t10
- covers: c1, h11, h12
- acceptance:
  - pyproject.toml is at 0.6.0 and uv sync has been re-run so whoami/overview report the new number
  - the CHANGELOG entry calls the user get array shape a BREAKING change explicitly, not just a change
  - README quickstart shows --file and --since usage
  - the version-check CI job passes (the version differs from main)

### t13 — Tell the two filing consumers about the breaking change

- instruction: Route through the communicate skill (agtag-backed, auto-signs). This is the overlooked-actor finding c30: neither repo watches this CHANGELOG, and both would break silently on the array change. Per h26/h27/h28 the success signals are met only when the consumers report their workarounds deleted — do not mark them met from our side.
- depends on: t11, t12
- covers: c30, h32, c2, h13, c11, h22, c24, h26, c26, h28
- acceptance:
  - a comment lands on issue #13 and on issue #14 naming 0.6.0 and the new user get array shape
  - the comments state what each repo can now delete: sensibo-cli's urllib multipart webhook workaround, jetson-ai-lab-cli's four local seam re-implementations
  - each comment is signed '- discord-bot-cli (Claude)'
  - the success signals are recorded as UNVERIFIED until the consumers report back — adoption is their action, not ours

## Risks

- [unknown_nonblocking] t4 and t5 are file-disjoint and land in the same wave, but both must emit an IDENTICAL --json attachment payload shape. Built in parallel by two agents, they can diverge in field names or nesting and still pass their own acceptance criteria. The merge gate must diff the two payload shapes, not just run both test files. (task t5)
- [unknown_nonblocking] The scan window moves while it pages: messages posted during a long walk of a busy channel land inside the requested window after the walk passed that point. Whether the coverage signal should account for this, or the window should close at a fixed upper bound taken at start, is undecided (frame park v6). (task t6)
- [unknown_nonblocking] t1 is the wave-1 serializer every later task builds on. If the widened fakes encode the WRONG discord.py semantics — particularly history()'s `oldest_first` default flip — every downstream task's tests pass against a fake that lies, and the bug ships green anyway. The fakes' ordering behaviour must be checked against the real library docstring, not against what the tasks expect. (task t1)
- [unknown_nonblocking] The live paging test (t12) needs a sandbox channel holding more than 100 messages inside the test window. #spark-tests may not have that history, in which case the test proves nothing while appearing to pass. Confirm the channel's message count before relying on that lane for c25/h27. (task t12)
- [follow_up] t13's success signals (c24/c25/c26) can only be met by the consumer repos reporting back. That is outside this plan's control and outside its timeline — the plan can complete with those signals still honestly unverified. (task t13)
- [unknown_nonblocking] Whether Discord's CDN attachment URLs carry signed expiry parameters was NOT checked during the challenge pass (frame park v7). If they do, the --json URLs are shorter-lived than c33's '404s once the message is deleted' wording implies, and t10's documentation would understate it. (task t10)

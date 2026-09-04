# Delivery Summary — Attachments + analysis-grade reads

plan: `attachments-analysis-grade-reads` · run: `complete` (12/13 tasks; `t13` blocked on an approval, not on work) · date: `2026-09-04`
baseline: `devague summary skeleton`

## Intent

Ship discord-bot-cli 0.6.0: file attachments on the write verbs (issue #13, filed by
sensibo-cli) and the read fields an analysis pipeline needs (issue #14, filed
by jetson-ai-lab-cli). The plan was seeded from a frame that went
through `/scope`, `/think` and `/challenge`, then fanned out to parallel
agents in isolated worktrees over seven dependency waves, each merge gated by
the test suite passing before and after.

## Planned Work

Quoted verbatim from the `devague summary` skeleton:

- `t1` — Widen tests/conftest.py fakes for every new surface
- `t2` — Add `discord_bot_cli`/cli/`_commands`/`_attachments.py` — the shared --file seam
- `t3` — Add `discord_bot_cli`/cli/`_commands`/`_timewindow.py` — parse --since into an aware UTC datetime
- `t4` — Wire --file into message post and message reply
- `t5` — Wire --file into thread post
- `t6` — Add the --since time window and coverage signal to channel messages
- `t7` — Give user get a batch form
- `t8` — Add author.bot and author.`global_name` to `_message_dict`()
- `t9` — Map the Discord 413 into the CLI error contract
- `t10` — Update the three hand-maintained self-teaching surfaces
- `t11` — Add the live-lane tests only a real Discord can prove
- `t12` — Release 0.6.0: version, CHANGELOG, README
- `t13` — Tell the two filing consumers about the breaking change

## Actual Delivery

| Plan task | Status | What actually landed |
|-----------|--------|----------------------|
| `t1` | delivered | Fakes reproduce discord.py 2.7.1 semantics including `history()`'s `oldest_first` default-flip; merge `67a4549` |
| `t2` | delivered | `_attachments.py`: `add_file_flag`, `build_files`, `require_content_or_files`, `attachments_payload`; merge `5eeb771` |
| `t3` | delivered | `_timewindow.py`: `parse_since` returns an always-aware UTC instant; merge `c57b31c` |
| `t4` | delivered | `--file` on `message post`/`reply`, `attachments` in `--json`; merge `b28c209` |
| `t5` | delivered | `--file` on `thread post`, identical payload shape; merge `1fb25d8` |
| `t6` | delivered | `--since` window, paging past 100, `window` coverage signal, ordering fixed; merge `fdc6932` |
| `t7` | delivered | Batch `user get` (varargs + `--ids-file`), always-array, exit 0 on per-id failure; merge `06569f7` |
| `t8` | delivered | `author.bot` + `author.global_name` with no extra `fetch_user`; merge `819ad65` |
| `t9` | delivered | 413 mapped with a boost-tier remediation **and the byte size sent**. `d2` was approved recording that the size was unreachable; the gap was then **closed** by threading the already-read size from `_attachments.upload_bytes` into `run()` (delta `b8` supersedes `b7`); merge `cc51eee` + follow-up |
| `t10` | delivered | catalog/learn/overview updated; one gap (`--ids-file` absent from learn's JSON) caught and fixed at the gate; merge `1a22f62` |
| `t11` | delivered | Live upload + paging tests, doubly gated, `pytest.fail` on a thin channel; merge `189e073`. **All 7 live tests since run and passing against real Discord**, after fixing a stale pre-0.6.0 assertion in `test_live_user_get` that only the live lane could catch |
| `t12` | delivered | 0.6.0 in pyproject + CHANGELOG (BREAKING called out) + README |
| `t13` | blocked | Not executed. Posts publicly to two other repos; the approved split plan specified "main agent + your OK", and that OK has not been given |

## Mid-work Decisions

- `d1` (approved) — Extend t7's file scope to include `tests/test_discord_integration.py`, and let the main agent apply the one-line fix at the merge gate rather than sending the task agent back. Reason: t7's confirmed scope omitted that file, whose line 45 asserted the OLD single-object `user get --json` shape; the approved always-array change necessarily invalidates it, and no task owned that file, so the plan as confirmed could not reach a green suite. A scoping error in the plan, not a failure by the task agent — which correctly refused to widen its own allowlist and reported the breakage.
- `d2` (**approved**) — t9's acceptance criterion 1 cannot be met as written: discord.py's `HTTPException` records only `response`/`status`/`code`/`text`, never the outgoing request's byte size, and the q2 decision forbids the pre-flight that would have captured it. The agent surfaced Discord's own text rather than inventing a number.
- Not covered by any deviation record: `--limit`'s argparse default moved from `20` to `None`, resolving to 20 only on the plain path, so a bare `--since` is not silently capped at 20. User-visible default unchanged.
- Not covered by any record: `m` in a `--since` duration means **months**, approximated as 30 days. The plan left the unit set open; the ambiguity with "minutes" is resolved in the docstring and the error hint.

## Drift From Plan

| Plan item | Reason for divergence | Classification |
|-----------|-----------------------|----------------|
| `t7` (`d1`) | t7's confirmed scope omitted `tests/test_discord_integration.py`, whose assertion encoded the old single-object shape that the approved breaking change invalidates | acceptable |
| `t9` (`d2`) | The 413 error could not name the byte size sent — discord.py's `HTTPException` never records it. **Since resolved**: the size is now threaded down from the verb that already read it, so the original criterion is met. `d2` stands as the record of the intermediate state | acceptable |
| `t13` | Not executed: outward-facing publication to two other repos, gated on an approval that was scoped into the split plan and not yet given | needs-follow-up |

## Evidence

- tests: full suite at `4f4882a` — **156 passed, 7 skipped** (baseline before the run: 61 passed, 5 skipped)
- tests: `tests/test_discord_channel.py::test_windowed_and_plain_reads_are_both_oldest_first` — pass
- tests: `tests/test_conftest_fakes.py::test_history_with_after_flips_default_to_oldest_first` — pass
- tests: `tests/test_timewindow.py` forced-TZ cases — pass
- tests: `tests/test_no_runtime_deps.py` — pass, **unmodified**
- tests: `tests/test_discord_client.py::test_413_stderr_shape_and_exit_code` — pass
- tests: live lane (`-m live`) — **7 passed** against the `#spark-tests` sandbox (guild `1413999242648748195`), `DISCORD_TEST_PAGING_SINCE=3650d`
- live evidence: a real upload returned attachment id `1545483523270377482`, a working signed CDN url, `size: 39`
- live evidence: `channel messages --since 3650d` returned **123 messages** oldest-first, `fully_covered: true`, `stopped_by: window_end`, in 2.5s
- live finding: the attachment URL carries `?ex=`/`&is=`/`&hm=`, decoding to exactly **24h** of validity (issued 2026-09-04T17:19:45Z)
- lint: `black --check`, `isort --check-only`, `flake8`, `bandit -c pyproject.toml -r discord_bot_cli` — all clean
- lint: `teken cli doctor . --strict` — 26/26 passed, 0 errors
- lint: `markdownlint-cli2` on README.md, CHANGELOG.md, CLAUDE.md — 0 errors
- commits: `3c7dfc8..017f3a3` (branch `spec/attachments-analysis-grade-reads`)
- devague ledger: 14 obligations (`o1`–`o14`), 14 evidence records (`e1`–`e14`), 5 behavioural deltas (`b1`–`b5`), 2 deviations (`d1` approved, `d2` proposed), 1 lapse (`l1` approved)
- issues: `#13`, `#14` (both still open — no comment posted)

## Delivery Claims

| Claim | Confidence | Evidence |
|-------|------------|----------|
| `--file` attaches multiple ordered files in one send across `message post`/`reply`/`thread post`, content optional | high | `e1` · merges `b28c209`, `1fb25d8` |
| Attachment path/count errors exit 1 with a remediation before login; no `OSError`/`ValueError` escapes | high | `e2` · `tests/test_attachments.py` |
| `--json` reports real attachment ids and URLs | high | `e15` — execution strength against real Discord: `test_live_message_post_with_file_upload` passed and a manual upload returned id `1545483523270377482`. Supersedes `e3`'s fidelity-only basis; risk `r8` closed |
| A `--since` window pages past the 100-message cap and reports coverage on every `--json` run | high | `e16` — 123 real messages returned in one windowed walk, above the >100 precondition. Supersedes `e4`'s fake-only basis; risk `r7` closed. `r9` (CI wiring) still open |
| Output is oldest-first on both the windowed and plain paths | high | `e8` · `test_windowed_and_plain_reads_are_both_oldest_first`, plus an independent end-to-end CLI run at the merge gate |
| `--since` always yields a tz-aware UTC instant, identical under any host TZ | high | `e9` · forced-TZ tests, plus independent verification under UTC / America/New_York / Asia/Kolkata |
| `author.bot` and `author.global_name` ship with no extra `fetch_user` call | high | `e5` · `test_channel_messages_author_fields_cost_no_extra_fetch_user_call` |
| `user get` resolves a batch in one login, always emits an array, exits 0 on per-id failure, preserves input order | high | `e6` · `tests/test_discord_user.py` · merge `06569f7` |
| Zero runtime dependencies is unchanged | high | `e7` · `tests/test_no_runtime_deps.py` passing **unmodified** |
| A 413 maps to the CLI error contract, naming the boost-tier dependence **and the byte size sent** | medium | `e18` — supersedes `e10`. Size threaded from `_attachments.upload_bytes`; nothing gates on it, asserted by `test_upload_bytes_is_reported_not_gated`. Still never exercised against a **real** oversized upload, which is why this is not `high` |
| `explain`/`learn`/`overview` describe the shipped surface | medium | `e11` — fidelity only; **no automated test asserts prose accuracy**, which is how the missing `--ids-file` entry was caught by hand |
| `--file` is documented as an unsandboxed local read | medium | `e12` · `explain message post`, `learn --json` |
| Live-test artifacts are documented as permanent | medium | `e13` · CLAUDE.md, README.md |
| An attachment URL is documented as a signed link expiring ~24h **and** 404ing on delete | high | `e17` — park `v7` answered live: the URL carries signed expiry decoding to exactly 24h. The earlier wording **did** understate it and was corrected in `catalog.py`, `learn.py` and `README.md` (delta `b6`) |
| sensibo-cli can delete its webhook multipart workaround | unverified | Consumer-side outcome; not told yet (`t13` blocked) |
| jetson-ai-lab-cli's report runs with no local seam re-implementations | unverified | Consumer-side outcome; not told yet (`t13` blocked) |
| Resolving 200 ids costs 1 invocation and 1 login | unverified | Architecturally true and unit-asserted, but never measured against a real 200-id scan |

**Lapse ledger evidence.** `l1` (approved, `control-absent`): during `/scope`,
9 candidate surfaces were explored inline where the skill mandates fanning out
to read-only subagents at 5 or more, and the lapse was filed late. Provenance
was unaffected — the main agent ran every move and each finding cites a real
file — but the independence a fan-out provides was absent. This caps confidence
in the *completeness* of the scope survey, not in any individual finding.

## Remaining Work / Follow-up

- `t13` — **blocked.** Post the 0.6.0 breaking-change notice to issues #13 and #14 via the `communicate` skill. Needs the user's explicit OK, as scoped in the approved split plan. Owner: user decision, then main agent.
- 18 evidence records, 14 obligations and 8 deltas are `proposed` and await `--confirm`/`--reject`. (`d1` and `d2` are approved; `l1` is approved; `b7` is superseded by `b8`.)
- `r9` — `DISCORD_TEST_PAGING_SINCE` is not wired into `.github/workflows/live-tests.yml`, so the paging test self-skips in CI even though it passes locally. No task owned that workflow file.
- The 413 path has never been exercised against a **real** oversized upload — only a synthesised `HTTPException`. Sending a file over the guild's cap is the only thing that would make `e18` fully trustworthy.
- `v6` — the scan window moves while it pages; whether the coverage signal should account for that, or close the window at a fixed upper bound taken at start, is undecided.
- Open frame parks `v2` (`--before` scope) and `v3` (per-guild `nick`) remain deliberately deferred.
- The `m` = months (30-day) duration unit is a judgement call that shipped; dropping `m` or renaming it `mo` is a one-line change in `_timewindow.py`.
- The live lane leaves **permanent artifacts** in `#spark-tests` — this run added a write chain, a thread, reactions and two file uploads. There is no `delete` verb.
- No PR opened yet — human gate 3.

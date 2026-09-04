# Skill upstream sources

discord-bot-cli vendors its `.claude/skills/` from **guildmaster** — the
AgentCulture **skills supplier** after the steward → guildmaster cutover
(guildmaster 0.5.0, 2026-05-24). `steward` retains the **alignment** role
(`steward doctor`, the sibling-pattern baseline); only the skills-supplier role
moved. This file tracks provenance so re-syncs stay deterministic.

Eight skills originate in
[`agentculture/devague`](https://github.com/agentculture/devague) — the
operator skills for its eight-leg method: `scope`, `think`, `challenge`,
`spec-to-plan`, `assign-to-workforce`, `deviate`, `validate-delivery`,
`summarize-delivery`. Guildmaster only **re-broadcasts** them, so devague is
the true origin in every case. Three of them (`think`, `spec-to-plan`,
`assign-to-workforce`) are vendored here via guildmaster's copy; the other five
are vendored **directly from devague** — see *Upstream choice for the devague
skills*, below.

Every vendored `SKILL.md` carries `type: command`. discord-bot-cli
declares a culture agent (`culture.yaml`, `backend: claude`), and
`core.skill_loader` silently skips any `SKILL.md` lacking `type:` — so the field
is load-bearing, even where guildmaster's upstream copy omits it.

| Skill | Upstream | Origin | Notes | Last synced |
|-------|----------|--------|-------|-------------|
| `cicd` | `../guildmaster/.claude/skills/cicd/` | guildmaster | CI/CD lane layered on `devex pr`: the 5 thin scripts (`workflow.sh`, `pr-status.sh`, `pr-reply.sh`, `_resolve-nick.sh`, `portability-lint.sh`) delegate lint/open/read/reply/delta to `devex` and add the `status` / `await` SonarCloud-gating extensions. Consumer-identifying prose (`guildmaster` → `discord-bot-cli`) adapted in the description + heading; upstream history (`Renamed from pr-review in steward 0.7.0; rebased on devex in 0.12.0`) and env-var literals (`STEWARD_*`) kept verbatim. The PR signature resolves at runtime from `culture.yaml` via `_resolve-nick.sh` (→ `discord-bot-cli`). Requires `devex` on PATH. | 2026-05-26 (guildmaster 0.6.0) |
| `communicate` | `../guildmaster/.claude/skills/communicate/` | guildmaster | Cross-repo + mesh communication. Consumer-identifying prose adapted in the description (incl. the `- discord-bot-cli (Claude)` signature line). **No hard-coded signature literal in the scripts** — `post-issue.sh` is `agtag`-backed and resolves the signing nick from `culture.yaml`; requires `agtag` (>=0.1) on PATH. The supplier `scripts/templates/` (`skill-update-brief.md`, `skill-new-brief.md`) are kept verbatim — inert for a consumer (they cite guildmaster as upstream). Renamed from `coordinate` in steward 0.8.0; absorbed `gh-issues` in 0.9.1. | 2026-05-26 (guildmaster 0.6.0) |
| `version-bump` | `../guildmaster/.claude/skills/version-bump/` | guildmaster | Pure-Python, CWD-aware (`scripts/bump.py`). Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `agent-config` | `../guildmaster/.claude/skills/agent-config/` | guildmaster (origin steward) | Shows a Culture agent's full config; run `scripts/show.sh` directly (no `guild` binary required). `scripts/show.sh` + `data/backend-fingerprints.yaml` verbatim. Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `doc-test-alignment` | `../guildmaster/.claude/skills/doc-test-alignment/` | guildmaster | **STUB** — `scripts/check.sh` exits not-yet-implemented; the contract lives in SKILL.md. Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `pypi-maintainer` | `../guildmaster/.claude/skills/pypi-maintainer/` | guildmaster | Switch a package install between PyPI / TestPyPI / local editable (`scripts/switch-source.sh`). Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `run-tests` | `../guildmaster/.claude/skills/run-tests/` | guildmaster | pytest + xdist + coverage (`scripts/test.sh`). Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `sonarclaude` | `../guildmaster/.claude/skills/sonarclaude/` | guildmaster | SonarCloud API queries (`scripts/sonar.sh`). Verbatim except added `type: command`. | 2026-05-26 (guildmaster 0.6.0) |
| `think` | `../guildmaster/.claude/skills/think/` | **devague** (re-broadcast via guildmaster) | idea→spec leg of the devague workflow chain. Verbatim (already carried `type: command` at guildmaster). Origin/broadcast prose left verbatim. | 2026-05-26 (guildmaster 0.6.0) |
| `spec-to-plan` | `../guildmaster/.claude/skills/spec-to-plan/` | **devague** (re-broadcast via guildmaster) | spec→plan leg of the devague workflow chain. Verbatim (already carried `type: command`). | 2026-05-26 (guildmaster 0.6.0) |
| `assign-to-workforce` | `../guildmaster/.claude/skills/assign-to-workforce/` | **devague** (re-broadcast via guildmaster) | plan→parallel-implementation leg of the devague workflow chain. Verbatim (already carried `type: command`). | 2026-05-26 (guildmaster 0.6.0) |
| `scope` | `../devague/.claude/skills/scope/` | **devague** (vendored direct) | idea→scope leg — the optional opening move ahead of `/think`. Method-only: `SKILL.md` alone, no `scripts/` resolver — the skill invokes the `devague` CLI directly. Byte-verbatim (already carried `type: command`). | 2026-09-04 (devague 0.24.1) |
| `challenge` | `../devague/.claude/skills/challenge/` | **devague** (vendored direct) | spec blind-spot pass, between `/think` and `/spec-to-plan`. Method-only: `SKILL.md` alone, no `scripts/` resolver — the skill invokes the `devague` CLI directly. Byte-verbatim (already carried `type: command`). | 2026-09-04 (devague 0.24.1) |
| `deviate` | `../devague/.claude/skills/deviate/` | **devague** (vendored direct) | execution-time leg: records human-approved departures from the confirmed plan. Method-only: `SKILL.md` alone, no `scripts/` resolver — the skill invokes the `devague` CLI directly. Byte-verbatim (already carried `type: command`). | 2026-09-04 (devague 0.24.1) |
| `validate-delivery` | `../devague/.claude/skills/validate-delivery/` | **devague** (vendored direct) | post-merge leg: runs the plan's behavioral tests agent-side and files evidence + behavioral deltas. Method-only: `SKILL.md` alone, no `scripts/` resolver — the skill invokes the `devague` CLI directly. Byte-verbatim (already carried `type: command`). | 2026-09-04 (devague 0.24.1) |
| `summarize-delivery` | `../devague/.claude/skills/summarize-delivery/` | **devague** (vendored direct) | closing leg: planned-versus-actual accountability artifact. Method-only: `SKILL.md` alone, no `scripts/` resolver — the skill invokes the `devague` CLI directly. Byte-verbatim (already carried `type: command`). | 2026-09-04 (devague 0.24.1) |

## Re-sync procedure

```bash
# Diff against upstream before pulling (example: cicd / communicate):
for s in cicd communicate; do
  diff -ru ../guildmaster/.claude/skills/$s .claude/skills/$s
done

# Pull a skill fresh (remove first so dropped scripts don't linger):
rm -rf .claude/skills/<skill>
cp -R ../guildmaster/.claude/skills/<skill> .claude/skills/

# ...except the five devague-direct skills, which re-sync from the origin
# (see "Upstream choice for the devague skills"):
for s in scope challenge deviate validate-delivery summarize-delivery; do
  rm -rf ".claude/skills/$s" && cp -R "../devague/.claude/skills/$s" .claude/skills/
done

# Re-apply the identifier-only adaptations in SKILL.md:
#   - consumer-identifying prose: `guildmaster` → `discord-bot-cli` (NOT
#     where it cites guildmaster/steward/devague as the upstream/origin).
#   - add `type: command` to the frontmatter if guildmaster's copy omits it
#     (load-bearing for the culture/claude backend's core.skill_loader).
# No script bodies are edited (cite-don't-import). The communicate signature
# resolves from culture.yaml via agtag — no literal to patch.
```

If a re-sync would lose a discord-bot-cli adaptation, lift the change
upstream into guildmaster first (per guildmaster's `docs/skill-sources.md`) and
re-vendor.

### Upstream choice for the devague skills (2026-09-04)

The five skills added on 2026-09-04 are vendored **straight from
`../devague/`**, not from guildmaster's re-broadcast, because guildmaster's
copies were materially stale at the time: they described devague's older
**six-leg** flow (`scope → think → spec-to-plan → assign-to-workforce →
deviate → summarize-delivery`), omitted the `challenge` and `validate-delivery`
legs from that chain, and `scope/SKILL.md` lacked the subagent fan-out rule
(4-or-fewer inline, 5-or-more fan out) that devague 0.24.1 ships. Guildmaster
carried no `validate-delivery` skill at all.

Vendoring from the origin is sanctioned by these skills' own provenance
sections — devague authors them and is *never* re-vendored back from
guildmaster's copy. Re-sync them from `../devague/`, not `../guildmaster/`,
unless and until guildmaster's broadcast catches up; the earlier three
(`think`, `spec-to-plan`, `assign-to-workforce`) still track guildmaster, so
this repo intentionally pulls the devague family from two upstreams. Folding
all eight onto one upstream is the cleanup to make once guildmaster
re-broadcasts current copies.

`.pr_agent.toml` came from the same pull (`../devague/.pr_agent.toml`). It is
not a skill, so it has no table row: it is the Qodo/PR-Agent reviewer config
holding the condensed form of `devague learn review` — the ledger-audit rules
(three-way evidence comparison, evidence-strength ceilings, deltas audited in
both directions). Vendored verbatim except its first comment line, which names
the consuming repo.

### Local divergence — `agex` → `devex` rename (2026-05-30)

The PR-lifecycle CLI was renamed `agex` → `devex` (same tool, new name). The
vendored `cicd` (`SKILL.md`, `workflow.sh`, `pr-status.sh`),
`assign-to-workforce`, and `communicate` (`skill-new-brief.md` template) copies
were **patched in place** for this rename rather than re-vendored — a deliberate
exception to cite-don't-import, made so the `cicd` scripts invoke the real
`devex pr` binary now. The matching canonical rename is tracked upstream for
guildmaster in [agentculture/guildmaster#48](https://github.com/agentculture/guildmaster/issues/48),
so the next clean re-sync from guildmaster reconciles without losing this
change. (Re-sync once guildmaster's renamed copies are broadcast.)

The same in-place patch also bumped the documented `devex` version floor from
`>=0.1` to `>=0.21` in the vendored `cicd` `SKILL.md` + `workflow.sh` (to match
this doc's tooling-prerequisites and the `await`-era feature set) — likewise
flagged for guildmaster on #48.

## Tooling prerequisites

- **`devex`** (>=0.21) on PATH — `cicd` delegates the PR lifecycle to `devex pr`.
- **`agtag`** (>=0.1) on PATH — `communicate` issue I/O wraps `agtag issue`.

Both ship on PATH in the standard AgentCulture dev setup (installed per the
devex / agtag READMEs).

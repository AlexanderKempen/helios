# Helios

Track and estimate AI development cost.

Helios helps you understand LLM usage at the feature level. It answers two questions:

- **What did this branch cost?**
- **What will this request likely cost before I run it?**

## Why

AI makes implementation cheaper. That shifts the bottleneck from writing code to deciding what is worth building and what is worth spending tokens on.

Helios makes that tradeoff visible.

## Install

Helios is a Python CLI published on PyPI. There is no npm package — `npm install helios`
installs an unrelated third-party module.

```bash
pipx install helios-cli      # recommended: isolated environment
# or
pip install helios-cli
# or run without installing
uvx --from helios-cli helios --help
```

Or from source:

```bash
git clone https://github.com/AlexanderKempen/helios.git
cd helios
pip install -e .
```

## Estimate a request

```bash
helios estimate "add csv export to dashboard"
helios estimate issue.md
helios estimate issue.md --repo-context
helios estimate issue.md --json
```

Example output:

```
╭──────────────────── helios estimate ─────────────────────╮
│                                                          │
│  Estimated cost:   $0.80 – $4.30                         │
│  Estimated tokens: 45k – 220k                            │
│  Scope:            medium                                │
│  Files touched:    4 – 12                                │
│  Risk:             moderate                              │
│  Confidence:       72%                                   │
│                                                          │
│  Recommendation:   Needs clarification                   │
│                                                          │
│  Ambiguities:                                            │
│    - Which export formats are required?                   │
│    - Should API and UI both be included?                  │
│                                                          │
│  Acceptance criteria:                                    │
│    - User can export dashboard data as CSV                │
│    - Export respects active filters                       │
│    - Download succeeds from dashboard                     │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

Helios highlights ambiguity and suggests acceptance criteria before you spend tokens on implementation.

## Track executed work

```bash
helios sync                # import usage from Claude Code sessions
helios report              # see cost per feature branch
helios run "your prompt"   # send prompt through Claude and track usage
helios analyze             # get cost optimization insights from Claude
```

## How it works

**Estimation** uses a hybrid approach:
1. Deterministic heuristics score prompt complexity (keywords, scope, UI/backend signals)
2. An LLM infers implementation breadth, risk, ambiguities, and acceptance criteria
3. Token estimates are converted to dollar ranges using model-specific pricing

**Tracking** reads Claude Code's session logs (`~/.claude/projects/`), extracts token usage per assistant response, and attributes cost to the git branch that was active. All data is stored locally in `~/.helios/helios.db`. `sync` is incremental and idempotent: re-running it (or syncing a rotated log) never double-counts an event.

Pricing lives in [`helios/data/pricing.json`](helios/data/pricing.json), keyed by model-id prefix
so dated snapshots (`claude-sonnet-4-5-20250929`) and vendor-prefixed ids
(`anthropic.claude-opus-5`) resolve to the right rates; unknown ids fall back to their model
family.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HELIOS_DB` | `~/.helios/helios.db` | Usage database location |
| `CLAUDE_CONFIG_DIR` | `~/.claude` | Where `sync` looks for session logs |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Releasing

Publishing runs from the `Release` workflow on a `v*` tag, using PyPI [trusted
publishing](https://docs.pypi.org/trusted-publishers/) — no API token is stored in the repo.
One-time setup: add a trusted publisher for `helios-cli` on PyPI pointing at this repository,
workflow `release.yml`, environment `pypi`.

```bash
# bump version in pyproject.toml, commit, then:
git tag v0.2.0 && git push origin v0.2.0
```

The workflow refuses to publish when the tag does not match the version in `pyproject.toml`.

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## License

MIT

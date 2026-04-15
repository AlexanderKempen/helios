# Helios

Track and attribute LLM usage (tokens + cost) to **git feature branches** during real development workflows.

Like ccusage, but for feature-level AI cost tracking.

## Install

```bash
pip install helios-cli
```

Or from source:

```bash
git clone https://github.com/AlexanderKempen/helios.git
cd helios
pip install -e .
```

## Quick start

```bash
# Import usage from your Claude Code sessions
helios sync

# See cost per feature branch
helios report
```

That's it. Zero config.

## Commands

### `helios sync`

Import usage from Claude Code interactive sessions. Reads the session logs in `~/.claude/projects/` and attributes token usage to the git branch that was active during each conversation.

Incremental — only imports new activity on each run.

```
$ helios sync
Syncing Claude Code sessions...
Imported 3,197 usage events from Claude Code.
```

### `helios run "prompt"`

Send a prompt directly through Claude CLI and track usage in one step.

```
$ helios run "build an API endpoint for user registration"
<Claude response>

[helios] feature=ai-search tokens=2,100 cost=$0.03
```

### `helios report`

Aggregated cost, tokens, and call count per feature branch, sorted by spend.

```
$ helios report

AI Usage Report

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Feature            ┃     Cost ┃     Tokens ┃ Calls ┃ Top Model       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ auth-refactor      │ $142.50  │ 9,500,000  │   85  │ claude-opus-4-6 │
│ billing-v2         │  $38.20  │ 2,540,000  │   42  │ claude-opus-4-6 │
│ search-indexing    │  $12.10  │   800,000  │   18  │ claude-opus-4-6 │
└────────────────────┴──────────┴────────────┴───────┴─────────────────┘
```

### `helios analyze`

Send your usage summary to Claude for cost optimization insights.

```bash
helios analyze
```

### `helios start`

Confirm tracking is active for the current branch (optional — all commands auto-detect the branch).

## How it works

1. `helios sync` reads Claude Code's JSONL session logs (`~/.claude/projects/`)
2. Extracts token usage, model, and git branch from each assistant response
3. Calculates cost using per-model pricing
4. Stores events in a local SQLite database (`~/.helios/helios.db`)
5. `helios report` aggregates per feature branch

All data stays local. No cloud, no auth, no config files.

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (for `sync` and `run` commands)

## License

MIT

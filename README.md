# claude-skill-audit

Score every Claude Code skill in `~/.claude/skills/` against the four-part activation pattern. Detect trigger collisions. Find dead skills. Run from CLI, cron, or a PreToolUse hook.

The four-part pattern was extracted from the gold-tier skills in [`anthropics/launch-your-agent`](https://github.com/anthropics/launch-your-agent) — `RedTeam`, `FirstPrinciples`, `SystemsThinking`, `BitterPillEngineering`, `IterativeDepth`, `ExtractWisdom`. They activate more reliably on natural-language prompts than the average skill because their descriptions follow a consistent four-part shape:

```yaml
description: "[Concrete domain sentence with specifics like file paths, versions,
canonical IDs.] Use when [explicit activation condition]. Triggers on \"phrase
the user types\", \"another phrase\", \"/slash-command\". NOT FOR [neighbor
case] (use `neighbor-skill`)."
```

This repo packages a scorer that checks every skill against that shape and reports gaps.

## Why

A Claude Code catalog of 100+ skills accumulates entropy. Half of them only fire when you type the slash command exactly. The other half collide on common phrases like "fix this" or "review". The four-part pattern is the recipe Anthropic's own reference skills use to stay reliable. This tool makes it cheap to keep your catalog at that bar.

## Install

```bash
# Option A: copy and run
curl -O https://raw.githubusercontent.com/SUDARSHANCHAUDHARI/claude-skill-audit/main/src/audit.py
python3 audit.py

# Option B: clone
git clone https://github.com/SUDARSHANCHAUDHARI/claude-skill-audit
cd claude-skill-audit
python3 src/audit.py
```

Requires Python 3.9+ and `pyyaml`.

## Usage

```bash
python3 src/audit.py
```

Sample output:

```
SKILL AUDIT REPORT — 2026-06-21
Total active skills: 182

Tier distribution (0-4 score against the four-part pattern):
  4 — Excellent (full pattern)     182
  3 — Good (3/4 parts)              0
  2 — Needs improvement             0
  1 — Poor                          0
  0 — Effectively dead              0

💥 TRIGGER COLLISIONS — none

SUMMARY: 182 excellent / 0 good / 0 need work / 0 missing SKILL.md
```

When a skill is missing parts:

```
🔴 CRITICAL — 1 skill(s)
  my-broken-skill                  score=1  missing=['use-when', 'triggers', 'not-for-boundary']

🟡 NEEDS IMPROVEMENT — 1 skill(s)
  my-okayish-skill                 missing=['triggers']

🟢 GOOD (one improvement away) — 3 skill(s)
  my-good-skill                    add=['not-for-boundary']
```

## The four parts in detail

### 1. Concrete domain sentence (first ~200 chars + period, or ≥200 chars)

What it does, with specifics. Not "Helps with X." Instead:

> "Generate a privacy policy HTML page and publish to GitHub Pages at the standard URL `https://example.com/privacy/[appname]/` covering data collected, third-party SDKs, retention, deletion, contact, and GDPR alignment."

### 2. `Use when …`

Or any variant: `Use after`, `Use before`, `Use for`, `Use at`, `Use as`, `Use immediately`, `Use whenever`. The explicit activation condition.

### 3. `Triggers on "phrase", "phrase", …`

Comma-separated phrases the user actually types. Real surface forms, not abstract topics. Include `/slash-command`. Include common variants ("ANR" + "application not responding").

### 4. `NOT FOR <case> (use \`neighbor-skill\`)`

Every neighbor that might collide. Each gets a redirect. This is the part most skills miss — without it, Claude has no way to know when *not* to fire.

## Companion tools

- **`cross-skill-test.py`** — given a user prompt, simulate which skills fire and rank by trigger overlap. Use before adding a new skill to verify no collision.
- **`skill-quality-guard.py`** (example PreToolUse hook) — warn/block on SKILL.md edits that drop below 3/4.
- **`skill-frequency.py`** — read `.skill_usage` files to surface ghost skills (created, never used).

## Recommended workflow

1. Run `audit.py` against your `~/.claude/skills/`
2. Tackle Critical (0-1/4) and Needs Improvement (2/4) tiers first
3. Run `cross-skill-test.py` against ambiguous prompts
4. Install the PreToolUse hook to prevent regressions
5. Add the audit to weekly cron — drift is invisible until it isn't

## The full story

This audit pattern was developed during a six-hour session that took my own Claude Code catalog from 9 → 182 skills at gold tier. Writeup: [Cleaning Up 173 Claude Code Skills](https://sudarshantechlabs.com/blog/cleaning-up-173-claude-code-skills).

## License

MIT. The pattern is from Anthropic's reference repo and freely usable.

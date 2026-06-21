#!/usr/bin/env python3
"""
skill-quality-guard.py — PreToolUse hook.

Validates that any new/edited SKILL.md description hits the four-part activation pattern:
  1. Concrete one-sentence domain/scope
  2. `Use when …` clause
  3. `Triggers on "…", "…"` keyword list (or `USE WHEN ..., ...` form)
  4. `NOT FOR <case> (use <neighbor>)` boundary

Fires only on Edit/Write touching ~/.claude/skills/*/SKILL.md.

Warns (does not block) for missing parts so the user can override. Blocks only when
description is completely missing or empty, which would make the skill un-activatable.
"""
from __future__ import annotations
import sys, json, re, os


def extract_desc_from_content(content: str) -> str:
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return ''
    fm = m.group(1)
    bm = re.search(r'^description:\s*[|>][^\n]*\n((?:[ \t]+.*\n?)+)', fm, re.MULTILINE)
    if bm:
        return ' '.join(l.strip() for l in bm.group(1).splitlines() if l.strip())
    sm = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
    return sm.group(1).strip() if sm else ''


def score_desc(desc: str):
    score = 0
    parts = []
    dl = desc.lower()
    if len(desc) >= 100 and ('.' in desc[:200]):
        score += 1; parts.append('concrete-sentence')
    if 'use when' in dl or 'use this skill when' in dl or 'use after' in dl or 'use before' in dl:
        score += 1; parts.append('use-when')
    if (re.search(r'triggers?\s+on[:\s].*"[^"]+"', desc, re.IGNORECASE)
        or re.search(r'use when\s+[a-z][^.]{20,}', desc, re.IGNORECASE)):
        score += 1; parts.append('triggers')
    if 'not for' in dl and ('use `' in dl or 'use /' in dl or 'use ' in dl):
        score += 1; parts.append('not-for-boundary')
    return score, parts


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = payload.get('tool_name') or payload.get('tool', '')
    if tool not in ('Edit', 'Write'):
        sys.exit(0)

    params = payload.get('tool_input') or payload.get('parameters') or {}
    path = params.get('file_path', '')
    if not path or 'SKILL.md' not in path or '/.claude/skills/' not in path:
        sys.exit(0)

    # For Write, the new content is in 'content'. For Edit, reconstruct from old/new.
    if tool == 'Write':
        new_content = params.get('content', '')
    else:
        new_string = params.get('new_string', '')
        # Without reading the file, we can only sanity-check the new_string portion.
        # If new_string contains a description: line, validate just that.
        if 'description:' not in new_string:
            sys.exit(0)
        new_content = new_string

    desc = extract_desc_from_content(new_content) if new_content.lstrip().startswith('---') else ''
    if not desc and 'description:' in new_content:
        # Edit-style: pull the description value out of the edit string
        sm = re.search(r'description:\s*(.+?)(?:\n[a-z_]+:|\n---|\Z)', new_content, re.DOTALL)
        if sm:
            desc = ' '.join(sm.group(1).split())

    if not desc:
        # No description visible in this edit — nothing to check.
        sys.exit(0)

    if len(desc) < 30:
        print(f"⛔ skill-quality-guard: description too short ({len(desc)} chars). "
              f"Activation will fail. Write a real description (≥100 chars, four-part pattern).",
              file=sys.stderr)
        sys.exit(2)

    score, parts = score_desc(desc)
    missing = [p for p in ['concrete-sentence', 'use-when', 'triggers', 'not-for-boundary'] if p not in parts]

    if score < 3:
        print(f"⚠️  skill-quality-guard: description scores {score}/4 — missing {missing}.\n"
              f"Four-part pattern: (1) concrete sentence, (2) Use when…, (3) Triggers on \"…\", "
              f"(4) NOT FOR neighbor (use other-skill). Run: python3 ~/.claude/skills/skill-audit/audit.py",
              file=sys.stderr)
        # Warn, don't block — user may be editing other parts of frontmatter
        sys.exit(0)

    if score == 3 and 'not-for-boundary' in missing:
        print(f"ℹ️  skill-quality-guard: description scores 3/4 (missing NOT FOR boundary). "
              f"Add: 'NOT FOR <neighbor case> (use \\`neighbor-skill\\`)' to hit gold tier.",
              file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Surface skill activation frequency, ghost skills, and cost-vs-use correlation."""
import os, json, glob
from datetime import datetime, timezone, timedelta
from collections import defaultdict

SKILLS = os.path.expanduser('~/.claude/skills')
NOW = datetime.now(timezone.utc)


def load_usage(skill_dir: str) -> dict:
    f = os.path.join(skill_dir, '.skill_usage')
    if not os.path.isfile(f):
        return {}
    try:
        return json.load(open(f, encoding='utf-8'))
    except Exception:
        return {}


def days_since(iso_ts: str) -> float:
    if not iso_ts:
        return float('inf')
    try:
        dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (NOW - dt).total_seconds() / 86400
    except Exception:
        return float('inf')


def main():
    rows = []
    for d in sorted(os.listdir(SKILLS)):
        full = os.path.join(SKILLS, d)
        if not os.path.isdir(full) or d.startswith('_'):
            continue
        skillmd = os.path.join(full, 'SKILL.md')
        if not os.path.isfile(skillmd):
            continue
        usage = load_usage(full)
        rows.append({
            'name': d,
            'use_count': usage.get('use_count', 0),
            'last_used_at': usage.get('last_used_at'),
            'days_idle': days_since(usage.get('last_used_at')),
            'created_at': usage.get('created_at'),
            'days_old': days_since(usage.get('created_at')),
            'state': usage.get('state', 'unknown'),
        })

    # Classify
    ghost = [r for r in rows if r['use_count'] == 0 and r['days_old'] > 30]
    stale = [r for r in rows if 0 < r['use_count'] and r['days_idle'] > 90]
    hot = sorted([r for r in rows if r['use_count'] > 0], key=lambda x: -x['use_count'])[:10]
    no_usage_file = [r for r in rows if not r['last_used_at'] and not r['created_at']]

    print(f"SKILL ACTIVATION FREQUENCY — {NOW.strftime('%Y-%m-%d')}")
    print(f"Total skills: {len(rows)}\n")

    print(f"🔥 TOP 10 BY USE COUNT")
    for r in hot:
        idle = f"{r['days_idle']:.0f}d idle" if r['days_idle'] != float('inf') else 'never'
        print(f"  {r['name']:36s} {r['use_count']:4d} uses · {idle}")
    print()

    print(f"👻 GHOST SKILLS — created >30d ago, never used ({len(ghost)} skills)")
    if not ghost:
        print("  (none — every skill has been touched)")
    else:
        for r in sorted(ghost, key=lambda x: -x['days_old'])[:20]:
            print(f"  {r['name']:36s}  {r['days_old']:.0f}d old, 0 uses")
    print()

    print(f"💤 STALE SKILLS — used, but >90d idle ({len(stale)} skills)")
    if not stale:
        print("  (none — all used skills are recent)")
    else:
        for r in sorted(stale, key=lambda x: -x['days_idle'])[:20]:
            print(f"  {r['name']:36s}  last used {r['days_idle']:.0f}d ago ({r['use_count']} total)")
    print()

    print(f"❓ NO USAGE TRACKING — never opened or counter file missing ({len(no_usage_file)} skills)")
    if no_usage_file:
        names = [r['name'] for r in no_usage_file]
        for i in range(0, len(names), 4):
            print("  " + "  ".join(f"{n:32s}" for n in names[i:i+4]))
    print()

    print(f"📊 SUMMARY")
    used = sum(1 for r in rows if r['use_count'] > 0)
    print(f"  Used at least once: {used}/{len(rows)} ({100*used/len(rows):.0f}%)")
    print(f"  Ghosts (>30d, 0 uses): {len(ghost)}")
    print(f"  Stale (>90d idle): {len(stale)}")
    print(f"  No tracking data: {len(no_usage_file)}")


if __name__ == '__main__':
    main()

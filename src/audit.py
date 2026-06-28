#!/usr/bin/env python3
"""Score every skill in ~/.claude/skills/ against the four-part activation pattern.

Pattern (lifted from anthropics/launch-your-agent gold-tier skills):
  1. One concrete domain sentence (≥100 chars, ends with period)
  2. `Use when …` clause
  3. `Triggers on "phrase", "phrase", …` with double-quoted phrases
  4. `NOT FOR <case> (use <neighbor>)` boundary

Score 0-4. Run quarterly or after adding new skills.
"""
import os, re, sys, json, argparse, datetime
from collections import defaultdict

SKILLS_DIR = os.path.expanduser('~/.claude/skills')
PARTS = ['concrete-sentence', 'use-when', 'triggers', 'not-for-boundary']


def extract_desc(path):
    """Extract the description field by parsing YAML — handles all forms (single-line, block, quoted multi-line)."""
    content = open(path, encoding='utf-8', errors='ignore').read()
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return ''
    try:
        import yaml
        parsed = yaml.safe_load(m.group(1))
        if isinstance(parsed, dict):
            desc = parsed.get('description', '')
            if isinstance(desc, str):
                # Collapse any internal whitespace runs into single spaces
                return re.sub(r'\s+', ' ', desc).strip()
        return ''
    except Exception:
        # Fall back to regex-based extraction
        fm = m.group(1)
        bm = re.search(r'^description:\s*[|>][^\n]*\n((?:[ \t]+.*\n?)+)', fm, re.MULTILINE)
        if bm:
            return ' '.join(l.strip() for l in bm.group(1).splitlines() if l.strip())
        sm = re.search(r'^description:\s*(.+)$', fm, re.MULTILINE)
        return sm.group(1).strip() if sm else ''


def score_desc(desc):
    score = 0
    present = []
    dl = desc.lower()
    # Concrete-sentence: description must be substantial AND have at least one
    # sentence boundary somewhere in the first 400 chars (or be >=200 chars overall).
    if len(desc) >= 100 and (('.' in desc[:400]) or len(desc) >= 200):
        score += 1
        present.append('concrete-sentence')
    # Accept any standard activation cue: Use {when|this skill when|after|before|on|for|at|as|immediately}
    if re.search(r'\buse\s+(when|this\s+skill\s+when|after|before|on|for|at|as|immediately|whenever)\b', dl):
        score += 1
        present.append('use-when')
    # Accept either: Triggers on "phrase", "phrase"   OR   USE WHEN phrase, phrase, phrase   OR   Triggers on: phrase, phrase
    if (re.search(r'triggers?\s+on[:\s].*"[^"]+"', desc, re.IGNORECASE)
        or re.search(r'use when\s+[a-z][^.]{20,}', desc, re.IGNORECASE)
        or re.search(r'triggers?\s+on[:\s]\s*[a-z][^.]{15,}', desc, re.IGNORECASE)):
        score += 1
        present.append('triggers')
    if 'not for' in dl and ('use `' in dl or 'use /' in dl or 'use ' in dl):
        score += 1
        present.append('not-for-boundary')
    return score, present


def collect_triggers(desc):
    # First unescape YAML-escaped quotes so we don't match the escape syntax as phrases
    cleaned = desc.replace('\\"', '"')
    phrases = re.findall(r'"([^"]+)"', cleaned)
    triggers = set()
    for p in phrases:
        p = p.strip().lower()
        # Filter: real triggers have letters, are reasonable length, aren't just punctuation
        if not p or not re.search(r'[a-z]', p):
            continue
        if not (3 <= len(p) <= 60):
            continue
        triggers.add(p)
    return triggers


def suggest_template(name, missing):
    """Emit a four-part description skeleton for a skill that scored low."""
    return (
        f'description: "[One concrete sentence about what {name} does, with specifics '
        f'like file paths, versions, or canonical IDs.] Use when [explicit activation '
        f'condition]. Triggers on \\"phrase the user types\\", \\"another phrase\\", '
        f'\\"/{name}\\". NOT FOR [neighbor case] (use `neighbor-skill`)."'
    )


def collect(skills_dir):
    rows = []
    trigger_owners = defaultdict(list)
    for d in sorted(os.listdir(skills_dir)):
        full = os.path.join(skills_dir, d)
        if not os.path.isdir(full) or d.startswith('_'):
            continue
        skillmd = os.path.join(full, 'SKILL.md')
        if not os.path.isfile(skillmd):
            rows.append((d, -1, [], '', 'NO SKILL.md'))
            continue
        desc = extract_desc(skillmd)
        s, parts = score_desc(desc)
        rows.append((d, s, parts, desc, ''))
        for t in collect_triggers(desc):
            trigger_owners[t].append(d)
    return rows, trigger_owners


def main():
    ap = argparse.ArgumentParser(description="Audit Claude Code skills against the four-part activation pattern.")
    ap.add_argument('--skills-dir', default=SKILLS_DIR, help="Skills directory (default: ~/.claude/skills)")
    ap.add_argument('--json', action='store_true', help="Emit machine-readable JSON instead of the text report")
    ap.add_argument('--fix', action='store_true', help="Print a suggested four-part description for each failing skill")
    ap.add_argument('--min-score', type=int, default=None, metavar='N', help="Exit nonzero if any skill scores below N")
    args = ap.parse_args()

    skills_dir = os.path.expanduser(args.skills_dir)
    if not os.path.isdir(skills_dir):
        print(f"Skills directory not found: {skills_dir}", file=sys.stderr)
        sys.exit(2)
    rows, trigger_owners = collect(skills_dir)
    collisions = {t: owners for t, owners in trigger_owners.items() if len(owners) > 1}

    if args.json:
        payload = {
            "date": str(datetime.date.today()),
            "total": len(rows),
            "skills": [{"name": d, "score": s, "present": p, "missing": [x for x in PARTS if x not in p] if s >= 0 else PARTS, "noSkillMd": s == -1} for d, s, p, _, _ in rows],
            "collisions": {t: owners for t, owners in collisions.items()},
        }
        print(json.dumps(payload, indent=2))
        below = any(0 <= s < args.min_score for _, s, _, _, _ in rows) if args.min_score is not None else False
        crit = any(0 <= s <= 1 or s == -1 for _, s, _, _, _ in rows)
        sys.exit(1 if (below or crit) else 0)

    total = len(rows)
    tier_counts = defaultdict(int)
    for r in rows:
        tier_counts[r[1]] += 1

    print(f"SKILL AUDIT REPORT — {datetime.date.today()}")
    print(f"Total active skills: {total}")
    print()
    print("Tier distribution (0-4 score against the four-part pattern):")
    labels = {
        4: "Excellent (full pattern)",
        3: "Good (3/4 parts)",
        2: "Needs improvement (2/4)",
        1: "Poor (1/4)",
        0: "Effectively dead (0/4)",
        -1: "MISSING SKILL.md",
    }
    for s in [4, 3, 2, 1, 0, -1]:
        if tier_counts[s]:
            print(f"  {s} — {labels[s]:36s}  {tier_counts[s]}")
    print()

    crit = [(d, s, p) for d, s, p, _, _ in rows if 0 <= s <= 1]
    if crit:
        print(f"🔴 CRITICAL — {len(crit)} skill(s)")
        for d, s, p in sorted(crit, key=lambda r: r[1]):
            missing = [x for x in ['concrete-sentence', 'use-when', 'triggers', 'not-for-boundary'] if x not in p]
            print(f"  {d:40s}  score={s}  missing={missing}")
        print()

    needs = [(d, s, p) for d, s, p, _, _ in rows if s == 2]
    if needs:
        print(f"🟡 NEEDS IMPROVEMENT — {len(needs)} skill(s)")
        for d, _, p in sorted(needs):
            missing = [x for x in ['concrete-sentence', 'use-when', 'triggers', 'not-for-boundary'] if x not in p]
            print(f"  {d:40s}  missing={missing}")
        print()

    good = [(d, p) for d, s, p, _, _ in rows if s == 3]
    if good:
        print(f"🟢 GOOD (one improvement away from Excellent) — {len(good)} skill(s)")
        for d, p in sorted(good):
            missing = [x for x in ['concrete-sentence', 'use-when', 'triggers', 'not-for-boundary'] if x not in p]
            print(f"  {d:40s}  add={missing}")
        print()

    missing_md = [d for d, s, _, _, _ in rows if s == -1]
    if missing_md:
        print(f"⚠️  MISSING SKILL.md — {len(missing_md)} skill(s)")
        for d in missing_md:
            print(f"  {d}")
        print()

    collisions = {t: owners for t, owners in trigger_owners.items() if len(owners) > 1}
    if collisions:
        print(f"💥 TRIGGER COLLISIONS — {len(collisions)} phrases claimed by ≥2 skills")
        for t, owners in sorted(collisions.items(), key=lambda x: -len(x[1]))[:30]:
            print(f"  \"{t}\"  →  {owners}")
        print()
    else:
        print("💥 TRIGGER COLLISIONS — none\n")

    print(f"SUMMARY: {tier_counts[4]} excellent / {tier_counts[3]} good / "
          f"{tier_counts[2] + tier_counts[1] + tier_counts[0]} need work / "
          f"{tier_counts[-1]} missing SKILL.md")

    if args.fix:
        failing = [(d, p) for d, s, p, _, _ in rows if 0 <= s <= 2]
        if failing:
            print("\n🔧 SUGGESTED FIXES (four-part description templates)")
            for d, p in sorted(failing):
                missing = [x for x in PARTS if x not in p]
                print(f"\n  {d}  (missing: {', '.join(missing)})")
                print(f"    {suggest_template(d, missing)}")

    # Exit nonzero if anything critical, or if --min-score gate fails
    below = any(0 <= s < args.min_score for _, s, _, _, _ in rows) if args.min_score is not None else False
    if crit or missing_md or below:
        sys.exit(1)


if __name__ == '__main__':
    main()

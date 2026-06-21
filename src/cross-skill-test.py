#!/usr/bin/env python3
"""Simulate skill activation for a given user prompt and score collision risk."""
import os, re, sys

try:
    import yaml
except ImportError:
    print("Install pyyaml: pip3 install pyyaml")
    sys.exit(1)

SKILLS = os.path.expanduser('~/.claude/skills')


def load_desc(skill: str) -> str:
    f = os.path.join(SKILLS, skill, 'SKILL.md')
    if not os.path.isfile(f):
        return ''
    content = open(f, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return ''
    try:
        parsed = yaml.safe_load(m.group(1))
        if isinstance(parsed, dict):
            return parsed.get('description', '') or ''
    except yaml.YAMLError:
        pass
    return ''


def split_not_for(desc: str):
    """Split description into main body and NOT FOR boundary."""
    nf = re.search(r'NOT FOR(.+)$', desc, re.IGNORECASE | re.DOTALL)
    if nf:
        return desc[:nf.start()], nf.group(0)
    return desc, ''


def score_prompt(prompt: str, desc: str):
    p = prompt.lower()
    body, not_for = split_not_for(desc)
    score = 0
    matches = []

    # +10 per quoted phrase in body matched
    for q in re.findall(r'"([^"]+)"', body):
        if q.strip() and q.lower() in p:
            score += 10
            matches.append(q)

    # +5 per significant un-quoted trigger word after "Triggers on:"
    trig = re.search(r'Triggers?\s+on[:\s]([^.]+)', body, re.IGNORECASE)
    if trig:
        for word in re.findall(r'\b([a-z][a-z\-]{4,})\b', trig.group(1).lower()):
            if word in p and word not in [m.lower() for m in matches]:
                score += 5
                matches.append(word)

    # -5 per quoted phrase in NOT FOR that matches the prompt
    for q in re.findall(r'"([^"]+)"', not_for):
        if q.strip() and q.lower() in p:
            score -= 5

    return score, matches


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("Usage: test.py <prompt> [--expect <skill-name>] [--top <N>]")
        sys.exit(1)

    prompt = sys.argv[1]
    expect = None
    top = 5
    if '--expect' in sys.argv:
        expect = sys.argv[sys.argv.index('--expect') + 1]
    if '--top' in sys.argv:
        top = int(sys.argv[sys.argv.index('--top') + 1])

    scores = []
    for d in os.listdir(SKILLS):
        full = os.path.join(SKILLS, d)
        if not os.path.isdir(full) or d.startswith('_'):
            continue
        desc = load_desc(d)
        if not desc:
            continue
        s, matches = score_prompt(prompt, desc)
        if s > 0:
            scores.append((d, s, matches))
    scores.sort(key=lambda x: -x[1])

    print(f"PROMPT: {prompt!r}\n")
    if not scores:
        print("NO SKILL MATCHES — prompt may need clearer keywords")
        sys.exit(1 if expect else 0)

    print(f"TOP {min(top, len(scores))} MATCHES:")
    for i, (d, s, m) in enumerate(scores[:top], 1):
        ms = ', '.join(repr(x) for x in m[:5])
        print(f"  {i}. {d:36s}  score={s:4d}  matched: {ms}")

    if len(scores) >= 2:
        gap = scores[0][1] - scores[1][1]
        threshold = max(5, 0.20 * scores[0][1])
        if gap < threshold:
            print(f"\n⚠️  COLLISION RISK — top two scores within {gap} pts")
            sys.exit(2)
        else:
            print(f"\n✓ Clear winner — gap of {gap} pts to runner-up")

    if expect:
        rank = next((i + 1 for i, x in enumerate(scores) if x[0] == expect), -1)
        if rank == 1:
            print(f"\nEXPECTED: {expect} ✅ (rank 1)")
        elif rank > 0:
            print(f"\nEXPECTED: {expect} ⚠️  (rank {rank}, not winner)")
            sys.exit(1)
        else:
            print(f"\nEXPECTED: {expect} ❌ (no match)")
            sys.exit(1)


if __name__ == '__main__':
    main()

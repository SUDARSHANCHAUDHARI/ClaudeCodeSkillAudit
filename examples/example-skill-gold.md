# Example: a skill that scores 4/4 (Excellent)

```yaml
---
name: privacy-policy-gen
description: "Generate or update a privacy policy HTML page for an Android/iOS app and publish to GitHub Pages at the standard URL `https://example.com/privacy/[appname]/`. Covers data collected, third-party SDKs, retention, deletion, contact, and GDPR/Play Store data-safety alignment. Use when launching a new app or updating an existing policy. Triggers on \"/privacy-policy-gen\", \"generate privacy policy\", \"create privacy policy\", \"publish privacy policy\", \"update privacy policy\", \"missing privacy policy\", \"privacy policy for [app]\". NOT FOR full GDPR audit (use `data-privacy-compliance`) or terms of service (use `terms-of-service-mega`)."
tools: Read, Write, Bash
---

# Privacy Policy Generator

[body content here]
```

Score:
- ✅ **Concrete sentence**: "Generate or update a privacy policy HTML page... at the standard URL `https://...`. Covers data collected, third-party SDKs, retention, deletion, contact, and GDPR/Play Store data-safety alignment."
- ✅ **Use when**: "Use when launching a new app or updating an existing policy."
- ✅ **Triggers**: 7 quoted phrases including `/slash`, natural-language variants, and a parametric form.
- ✅ **NOT FOR**: 2 neighbors named with explicit redirects.

# Example: a skill that scores 1/4 (Poor)

```yaml
---
name: privacy-policy-mega
description: GDPR/CCPA compliant privacy policy generator. More detailed than privacy-policy-gen skill.
tools: Read, Write
---
```

Score:
- ✅ Concrete sentence (barely — 80 chars)
- ❌ No Use-when clause
- ❌ No quoted triggers
- ❌ No NOT FOR boundary

This skill won't activate reliably. It only fires on `/privacy-policy-mega`. Even worse, the description name-checks `privacy-policy-gen` as if it's an upgrade — creating ambiguity at activation time. Either rewrite to 4/4 or archive.

# Example: a skill that scores 3/4 (Good — missing only NOT FOR)

```yaml
---
name: ship-check
description: "Run a final pre-ship check before release — version, tests, lint, secrets, README. Use before every Play Store / App Store release. Triggers on \"ship check\", \"ready to ship\", \"pre-release\", \"before I release\", \"/ship-check\"."
tools: Bash, Read
---
```

Score:
- ✅ Concrete sentence
- ✅ Use before
- ✅ Quoted triggers
- ❌ No NOT FOR (collides with `release-sudarshan` on "ready to ship")

Fix: add `NOT FOR the release itself (use \`release-sudarshan\`) or post-release doc sync (use \`document-release\`).`

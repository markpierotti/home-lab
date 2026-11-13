---
title: "Source register"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, knowledge-management]
sources: []
confidence: high
contested: false
contradictions: []
---

# Source register

Architecture read during setup:

- Existing Voltron vault `SYSTEM.md`: capture, triage, single task list, archive and monitor ownership.
- Existing Voltron `SCHEMA.md`: frontmatter, provenance, wikilinks, contradictions and review.
- `concepts/medallion-architecture.md`: Raw → Review → Wiki; review before trusted promotion.
- `concepts/voltron-documentation-system.md`: chat is not canonical; preserve meaningful evidence and decisions.
- `learning-loop/README.md`: source integrity, candidate guidance, independent review and explicit limits; not copied as an automated learning engine.
- Hermes skill `voltron-capture-pipeline/SKILL.md`: do not delete or rename iCloud vault folders; account for iCloud file eviction.
- Hermes Obsidian skill: filesystem-first Markdown and resolved vault paths.
- Live Slim configuration and installed source inspected on 20 October: retention, schedules, SQLite store and backup sources.

Existing Voltron path was resolved from Obsidian's registered vault to the actual lowercase `voltron` directory. This new vault uses a distinct lowercase `slim-telemetry` directory; it does not rename Voltron or install plugins.

The setup code and tests are retained locally in `~/Documents/Slim-Vault-Setup`. No source repository was pushed or merged.

Related: [[architecture]] · [[SCHEMA]] · [[log]]

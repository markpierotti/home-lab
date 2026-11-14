---
title: "Schema"
created: 2026-10-20
updated: 2026-10-20
type: summary
tags: [slim, knowledge-management]
sources: []
confidence: high
contested: false
contradictions: []
---

# Schema

## Names and frontmatter

Use lowercase hyphenated note names, apart from the conventional `SYSTEM.md`, `SCHEMA.md` and `Tasks.md`. Add every maintained knowledge page to [[index]]. Include title, created, updated, type, tags, sources, confidence, contested and contradictions in YAML. Use at least two useful outbound wikilinks per maintained page. Bump updated when changing a page.

Types: entity, concept, comparison, query, summary. Tags: slim, telemetry, asus, home-lab, hermes, obsidian, knowledge-management, evidence, review, incident, retention, backup, operations, security.

Sources must distinguish live observations, copied records, user reports and model interpretations. Unknown values remain unknown. For multi-source synthesis, cite individual source paths beside material claims. Confidence describes the claim supported by those sources, not confidence in a model.

## Raw records

`raw/objects/<first-two-hex>/<sha256>.gz` contains exact captured bytes. `raw/captures/<local-date>/<UTC timestamp>.json` records each changed source, object digest, byte count and capture failures. Paired Markdown receipts expose captures in Obsidian. A hash proves internal byte consistency, not that an underlying event happened.

## Review and promotion

Capture receipts and incident proposals are unreviewed. Mark must approve a specific proposal before it becomes a curated finding in `Wiki/`. Record the approval, exact source manifests and any disagreement. Preserve superseded versions in `_archive/` and append the change to [[log]].

Related: [[SYSTEM]] · [[source-register]]

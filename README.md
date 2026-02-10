# CaRMS Mini Data Platform

## Overview

This project is a small, reproducible data platform built on top of publicly available CaRMS program description data. The goal is to demonstrate how heterogeneous, text-heavy datasets can be ingested, normalized, and made queryable in a reliable way using a modern PostgreSQL + Python stack.

Rather than starting with modeling or analytics, the focus is on **data correctness, lineage, and queryability**, which are prerequisites for downstream analysis, reporting, and simulation.

The end result is a Postgres-backed warehouse that allows reviewers to run SQL queries against program metadata and multiple representations of program descriptions.

---

## Key Design Principles

### Evidence before assumptions

The source data includes multiple overlapping exports of program descriptions:
- HTML JSON
- Markdown JSON
- Enriched Markdown files
- Sectioned CSVs

Rather than assuming these were separate datasets, the project:
- inspected each source independently
- established stable identifiers empirically
- quantified similarity across representations
- verified that the data represents the same underlying content at different pipeline stages

This led to a **single-document, multi-representation model** instead of premature deduplication.

---

### Unify on identity, not content

Each program description is uniquely identified by:
- `match_cycle_id`
- `program_stream_id`
- `doc_id = <match_cycle_id>-<program_stream_id>`

All representations are linked to this identity. Content is **not merged or collapsed**, preserving lineage and allowing future comparison or reprocessing.

---

### Representations are optional

Different datasets provide different “views” of the same document:
- canonical markdown
- raw HTML
- enriched markdown with linkification
- section-level extraction

The schema does not assume all representations exist for all documents. Missing representations are treated as normal and handled explicitly.

---

## Data Model

### Tables

#### `discipline`
Reference table defining medical disciplines.

#### `program_stream`
One row per program stream in a match cycle. Acts as the registry tying disciplines, schools, and streams together.

#### `program_description_artifact`
Stores textual program descriptions. One row per `(doc_id, representation)` pair.

Key fields:
- `doc_id`
- `program_stream_id`
- `match_cycle_id`
- `representation`
- `content`
- `source_file`
- `content_sha256`
- `ingested_at`

A uniqueness constraint on `(doc_id, representation)` prevents duplication while allowing multiple representations.

---

## Canonical Access with Fallback

A canonical SQL view (`v_program_description_canonical`) provides exactly one “best available” description per program stream using explicit fallback logic:

1. `markdown_v2`
2. `markdown_enriched`
3. `html_v2`

This centralizes representation preference and prevents downstream query duplication or failure due to missing data.

---

## Orchestration and API

### Dagster

A minimal Dagster pipeline materializes the warehouse:
- loads core reference tables
- ingests all description representations
- creates the canonical fallback view
- emits metadata such as row counts

Run locally with:

```bash
dagster dev -m carms_platform.etl.definitions
```

## Development Notes

- **Approximate time spent:** ~7 hours end-to-end (environment setup, data inspection, schema design, ingestion, visualization, orchestration, API, documentation).
- **Use of AI tooling:** ChatGPT was used as a development aid for brainstorming, debugging, and iteration (similar to documentation search). Final decisions and validation were performed locally by the author.

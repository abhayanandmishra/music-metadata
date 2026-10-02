# Music Organizer Planning Spec Prompt

You are planning a music organizer workflow for `music_organizer.py`.

## Goal
Create a robust plan that processes music files one-by-one, cleans and writes metadata safely, supports missing metadata fallback, and provides a UI for editing plus search/filter.

## Scope
1. Iterate through supported music files one at a time.
2. Read metadata tags (artist, title, album, track, genre, year, original filename stem).
3. Normalize and clean metadata.
4. Apply domain rules:
- Remove known noise words.
- Remove year tokens from album.
- Normalize track format.
5. Handle missing metadata via fallback process from filename/folder clues.
6. Save cleaned metadata back into files with corruption protection.
7. Rename files using default pattern `{album} - {title}`.
8. Build UI for listing files, editing metadata, saving updates, and processing all files.
9. Add search/filter by filename and metadata attributes.
10. Include dry-run mode and explicit error handling.
11. Add a separate missing-metadata process that accepts metadata from CLI or JSON and writes it back to files.
12. Generate a report of changes and errors for all processed files.
13. Validate report correctness with deterministic checks (record counts, totals, rename outcomes, and error tally).
14. Use directory structure `music/ip`, `music/op`, and `music/nc`.
15. Route missing-metadata follow-up workflow to read files from `music/nc`.
16. Use dry-run by default with report generation enabled; require `--apply` to make file changes.
17. Add test cases for normal flow, edge cases, and error scenarios.

## Non-Functional Requirements
- Do not corrupt media content while writing tags.
- Keep logs transparent and actionable.
- Preserve extension and resolve rename collisions safely.
- Keep report schema stable for automated validation.
- Keep directory workflow predictable (`ip` input, `op` processed output, `nc` no-change/missing-metadata backlog).

## Deliverables
- Milestone plan with implementation order.
- Risk list and mitigations.
- Validation checklist for dry-run, `--apply` run, and report verification.
- Report schema definition (per-file metadata before/after, rename outcome, and error list).
- Test plan with concrete test cases (unit + integration style checks).

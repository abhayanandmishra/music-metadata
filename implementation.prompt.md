# Music Organizer Implementation Spec Prompt

Implement the music organizer in `music_organizer.py` with these requirements.

## Functional Requirements
1. Read each music file one-at-a-time.
2. Extract metadata using mutagen easy tags.
3. Clean metadata:
- strip whitespace
- remove noise words
- remove year from album
- normalize separators and track number
4. For missing metadata, run fallback process:
- infer album/title/artist from filename segments and parent folder
5. Write cleaned metadata back to file:
- create backup
- write tags
- validate output file integrity (size > 0)
- restore from backup on failure
6. Rename by pattern; default is `{album} - {title}`.
7. Print metadata blocks before rename operations.
8. Provide dry-run output for metadata updates and renames.
9. Build GUI:
- folder selection and scan
- file list
- editable metadata fields
- apply clean, save metadata, rename selected, process all
- search/filter field
10. Error handling:
- unsupported/unreadable files
- write failures
- rename collisions/target exists
11. Missing metadata external input process:
- accept metadata via JSON file argument
- accept metadata via inline CLI JSON argument
- format must match metadata keys and be keyed by file name/stem/path
- only fill missing metadata fields from this input
12. Report generation:
- write JSON report with per-file original metadata, cleaned metadata, update/rename status
- include all errors encountered
- include totals summary
13. Directory structure workflow:
- input from `music/ip`
- processed output to `music/op`
- no-change or unresolved metadata files to `music/nc`
14. Missing metadata follow-up process:
- second-pass workflow reads from `music/nc`
- accepts CLI/JSON metadata patches and retries metadata/tag updates
15. Dry-run default and apply switch:
- default behavior is dry-run and report generation
- `--apply` enables metadata write + file moves/renames
16. Report validation mode:
- validate report totals against file entries
- verify processed count and error count consistency
- fail fast on schema mismatches
17. Tests:
- add tests for happy path, no-change routing, missing metadata flow, report validation, and error scenarios

## Acceptance Criteria
- Running default mode reports metadata and rename plan without changes.
- Running with `--apply` writes metadata and renames/moves files safely.
- UI supports discovery, edit, search/filter, and update workflows.
- Missing metadata files get fallback values and can be renamed by default pattern.
- Missing metadata can be supplied from CLI/JSON and is written safely to files.
- A report file is generated when requested, containing metadata changes and errors.
- Files are organized into `music/ip`, `music/op`, and `music/nc` according to outcomes.
- Report validation can confirm report integrity and totals.

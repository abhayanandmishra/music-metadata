# Music Organizer Spec Gap Analysis

**Date:** 2026-09-30  
**Status:** Gap Verification Report

---

## Executive Summary

The Music Organizer Specification comprehensively addresses all 17 scope items and non-functional requirements from the planning prompt. However, **15 logical gaps** have been identified that require clarification to ensure complete and unambiguous implementation. These gaps are categorized as **specification ambiguities** rather than missing features—all required capabilities are present, but behavioral details need explicit definition.

---

## Verification Status

### ✅ Requirements Fully Addressed (17/17)

| # | Requirement | Section | Status |
|---|---|---|---|
| 1 | Iterate through supported music files one-at-a-time | 2.1.1, 5.1 | ✓ |
| 2 | Read metadata tags (artist, title, album, track, genre, year, filename stem) | 2.1.1 | ✓ |
| 3 | Normalize and clean metadata | 2.1.2 | ✓ |
| 4a | Remove noise words domain rule | 2.1.2 (2) | ✓ |
| 4b | Remove year from album domain rule | 2.1.2 (3) | ✓ |
| 4c | Normalize track format domain rule | 2.1.2 (4) | ✓ |
| 5 | Handle missing metadata via fallback process | 2.1.3 | ✓ |
| 6 | Save cleaned metadata with corruption protection | 2.1.4 | ✓ |
| 7 | Rename files using default pattern {album} - {title} | 2.2.1 | ✓ |
| 8 | Build UI for file listing, editing, saving, processing | 5.2 | ✓ |
| 9 | Add search/filter by filename and attributes | 5.2 | ✓ |
| 10 | Include dry-run mode and error handling | 2.4.1, 2.5 | ✓ |
| 11 | Add separate missing-metadata process with CLI/JSON input | 2.1.3 (3), 2.3.3 | ✓ |
| 12 | Generate report of changes and errors | 2.6 | ✓ |
| 13 | Validate report with deterministic checks | Section 8.3 | ✓ |
| 14 | Use directory structure music/ip, music/op, music/nc | 2.3.1 | ✓ |
| 15 | Route missing-metadata follow-up to read from music/nc | 2.3.3 | ✓ |
| 16 | Dry-run default, require --apply for changes | 2.4.1, 2.4.2 | ✓ |
| 17 | Add test cases for normal, edge, error scenarios | Section 9 | ✓ |

---

## Identified Gaps & Clarifications Needed

### **GAP #1: Logging System Architecture Not Specified**

**Plan Reference:** "Keep logs transparent and actionable"  
**Spec Section:** 2.5.2, Section 10.2  
**Issue:** The spec mentions logging errors but doesn't define:
- Log format (plain text, JSON, structured logs)
- Log levels (DEBUG, INFO, WARN, ERROR)
- Log output destination (console, file, both)
- Log file location and rotation policy
- Which events trigger logging (successful writes, collisions, fallbacks)

**Impact:** Implementation detail—developers must guess logging strategy  
**Recommendation:**
```
### 2.7 Logging System

#### 2.7.1 Log Format
- Plain text format: "[TIMESTAMP] [LEVEL] [COMPONENT] Message"
- Log levels: DEBUG, INFO, WARN, ERROR
- Timestamp format: ISO8601 with milliseconds
- One log entry per line

#### 2.7.2 Log Output
- Console: Always output errors to stderr, info to stdout
- Log file: Optional, path via --log-file argument
- Default: No log file (console only)

#### 2.7.3 Log Events
- DEBUG: File scanner iteration, metadata field reads, pattern matching
- INFO: File processed, metadata cleaned, rename outcome, routing decision
- WARN: Fallback applied, collision detected, encoding issue
- ERROR: Read failure, write failure, validation error, move failure

#### 2.7.4 Log Rotation (if file-based)
- Max size: 50MB per file
- Max files: 5 rotations kept
- Format: music_organizer.log, music_organizer.log.1, etc.
```

---

### **GAP #2: Metadata Console Output During Processing**

**Plan Reference:** "Print metadata blocks before rename operations"  
**Spec Section:** 5.1 (CLI Workflow)  
**Issue:** Spec doesn't specify:
- Should metadata be printed to console during processing (before/after comparison)?
- When? (For all files or just renamed files?)
- What format? (Key=Value table, JSON, custom format)
- Should this be suppressible via --quiet flag?

**Impact:** UX detail—users won't see processing progress without this  
**Recommendation:**
```
### 2.8 Processing Output Display

#### 2.8.1 Console Output (During Processing)
In dry-run and apply modes, print to stdout:

**For each processed file:**
```
=== File: original_filename.mp3 ===
Original:
  artist: [value or "MISSING"]
  title: [value or "MISSING"]
  album: [value or "MISSING"]
  track: [value or "MISSING"]

Cleaned:
  artist: [value or "MISSING"]
  title: [value or "MISSING"]
  album: [value or "MISSING"]
  track: [value or "MISSING"]

Action: Rename to: new_filename.mp3 → Route to: op/ [or errors]
```

#### 2.8.2 Suppression
- Add `--quiet` flag to suppress per-file output
- Always output summary at the end
```

---

### **GAP #3: Default Noise Words List**

**Plan Reference:** "Remove known noise words" (domain rules)  
**Spec Section:** 2.1.2 (2), 4.2  
**Issue:**
- Spec says config file should include noise words list
- No default list provided
- Should defaults be hardcoded or loaded from file?

**Impact:** Implementation detail—unclear what words to remove  
**Recommendation:**
```
### Default Noise Words Configuration

Hardcoded defaults (can be overridden in config.yaml):
```yaml
noise_words:
  - Remastered
  - Remastered Edition
  - Deluxe Edition
  - Album Version
  - Single Version
  - Extended Mix
  - Explicit
  - Clean Version
  - Radio Edit
  - Demo
  - Live
  - Acoustic Version
  - Instrumental
  - (Bonus Track)
  - [Bonus Track]
```

- Applied to: album, title fields only
- Matching: case-insensitive, word-boundary regex
- Remove entire word occurrence, collapse resulting spaces
```

---

### **GAP #4: Dry-Run Report File Generation Behavior**

**Plan Reference:** "Dry-run by default with report generation enabled"  
**Spec Section:** 2.4.1, 2.6.1  
**Issue:**
- Spec says report is "generated automatically"
- But doesn't clarify: Does dry-run WRITE the report file or print to console only?
- Should there be --no-report flag to skip report generation?
- Should --dry-run automatically use --report-file with timestamp? (e.g., `report_2026-09-30_120000.json`)

**Impact:** Workflow detail—users might get confused by duplicate report files  
**Recommendation:**
```
#### 2.4.1 Dry-Run Mode (Revised)
- Generate report to --report-file location (overwrites by default)
- Add `--no-report` flag to skip report generation
- Add `--report-timestamp` flag to append timestamp to report filename
- Report shows "proposed" values for rename and routing (not "actual")
- No files are modified
```

---

### **GAP #5: Missing Metadata Distinction in Routing**

**Plan Reference:** `music/nc` for "no-change/missing-metadata backlog"  
**Spec Section:** 2.3.2  
**Issue:**
- Spec routes only "unresolved missing metadata" to `nc/`
- But what about files with complete metadata that don't need rename?
- Should they be moved to `op/` even if rename != original filename?
- Or stay in `ip/` as "no-change"?

**Impact:** Directory workflow clarity—ambiguous routing logic  
**Recommendation:**
```
#### 2.3.2 Routing Rules (Clarified)

**Routing Decision Tree:**

1. **Check for errors** (unsupported, unreadable, write failure)
   → Route to `nc/` with error code, mark as "error"

2. **Check for missing metadata after fallback + external patches**
   → If artist OR title OR album is still missing/empty
   → Route to `nc/`, mark as "missing_metadata"

3. **Check if rename differs from original filename**
   → If YES (file needs renaming)
   → Route to `op/`, rename and move file

4. **Default (file OK, no rename needed)**
   → Route to `op/` (or stay in `ip/` with no-move flag?)
   → Mark as "no_change"

**Behavior in --apply mode:**
- `nc/`: Physically move file
- `op/`: Rename and move file (or just move if no rename needed)
- Unmodified: Option to leave files in `ip/` if no errors and no changes required

**Proposed Enhancement:**
Add routing status to report: "error", "missing_metadata", "no_change", "renamed"
```

---

### **GAP #6: Filename Collision Resolution Strategy**

**Plan Reference:** "Resolve rename collisions safely"  
**Spec Section:** 2.2.2  
**Issue:**
- Spec says append numeric suffix (e.g., `filename_1.mp3`, `filename_2.mp3`)
- But doesn't specify:
  - What if `filename_1.mp3` already exists?
  - Increment until free? (filename_1, filename_2, filename_3...)
  - Or use hash-based suffix?
  - Maximum collision depth?

**Impact:** Implementation detail—collision resolution algorithm  
**Recommendation:**
```
#### 2.2.2 Collision Handling (Detailed)

**Algorithm:**

1. Determine proposed filename from pattern
2. Check if file exists in target directory (op/)
3. If collision detected:
   - Extract base filename and extension
   - Try appending _1, _2, _3... up to _999
   - Return first available filename
   - Log collision: "Collision for 'Song.mp3', resolved to 'Song_5.mp3'"
4. Store both "proposed" and "actual" filename in report
5. Max collision attempts: 999 (fail with error if exceeded)

**Example:**
```
Original: "song.mp3"
Proposed: "Album - Song.mp3"
Exists:   "Album - Song.mp3" (file in op/)
Result:   "Album - Song_1.mp3"
Also Exists: "Album - Song_1.mp3", "Album - Song_2.mp3"
Try:      "Album - Song_3.mp3" ✓ (available)
```
```

---

### **GAP #7: Filename Character Sanitization Rules**

**Plan Reference:** "Preserve extension and resolve rename collisions safely"  
**Spec Section:** 2.2.1  
**Issue:**
- Spec says "remove/replace invalid filesystem characters"
- Doesn't specify which characters or replacement strategy
- Windows vs. Linux/Mac have different restrictions
- Should behavior be configurable?

**Impact:** Cross-platform consistency—different platforms have different rules  
**Recommendation:**
```
#### 2.2.1 Filename Sanitization (Detailed)

**Invalid Characters (Removed or Replaced):**

Universal (all platforms):
- / → _
- \ → _
- : → -
- * → _
- ? → _
- " → '
- < → (
- > → )
- | → -

Windows Additional (when running on Windows):
- CON, PRN, AUX, NUL, COM1-9, LPT1-9 (reserved names)
  → Prefix with underscore if filename matches

**Scenario Examples:**
```
Input: "Song: Best * Ever"
Output: "Song- Best _ Ever"

Input: "Artist/Album/Song"
Output: "Artist_Album_Song"

Input: "It's the "Best" Song"
Output: "It's the 'Best' Song"
```

**Max Filename Length:**
- 255 bytes (filesystem limit)
- If sanitized filename exceeds: truncate and warn
- Preserve extension always

**Configuration:**
Add `filename_sanitize_strategy` to config.yaml:
- "remove": Delete invalid chars (default)
- "replace": Replace with underscore
```

---

### **GAP #8: Fallback Priority & Data Merge Strategy**

**Plan Reference:** "Handle missing metadata via fallback process"  
**Spec Section:** 2.1.3  
**Issue:**
- Spec lists fallback sources: filename → folder → external JSON
- Doesn't specify priority when multiple sources provide data for same field
- Should external JSON override filename hints? (Currently says "fill missing" but ambiguous)
- What if external JSON has conflicting data?

**Impact:** Data integrity detail—unpredictable behavior in edge cases  
**Recommendation:**
```
#### 2.1.3 Missing Metadata Fallback (Clarified)

**Priority Order (First with data wins):**

1. **Original file metadata** (if present and non-empty)
2. **External metadata input** (--metadata-json or --metadata-inline-json)
3. **Filename parsing** (pattern-based inference)
4. **Parent folder hints** (heuristics from directory structure)
5. **Leave empty** (if all sources fail)

**Non-Destructive Merge Rule:**
- Only fill fields that are currently empty or None
- Never overwrite existing metadata with fallback/external data
- Exception: External JSON keyed with explicit intent (e.g., force=true)
- Document per-file which fields were filled and from which source

**External JSON Structure (Extended):**
```json
{
    "song.mp3": {
        "artist": "Artist Name",
        "album": "Album Name",
        "_note": "Filled artist and album from external source"
    }
}
```

**Report Tracking:**
```json
{
    "fallback_applied": true,
    "fallback_sources": {
        "artist": "filename",
        "album": "folder_hint",
        "title": "original"
    },
    "external_metadata_applied": true
}
```
```

---

### **GAP #9: File Move Error Recovery**

**Plan Reference:** "Do not corrupt media content" (data safety)  
**Spec Section:** 2.1.4, 2.5.2  
**Issue:**
- Spec covers backup/restore for write failures
- Doesn't address: What if metadata write succeeds but file move fails?
- Should file be left in `ip/`, or moved back if `op/` operation fails?
- What's the recovery behavior?

**Impact:** Data safety—unclear recovery path for multi-step operations  
**Recommendation:**
```
#### 2.1.4 Write & Move Safety (Enhanced)

**Write Metadata (2 steps):**
1. Create backup of original file before writing
2. Write tags to file, validate output
3. On validation failure: Restore from backup immediately
4. Clean up backup file on success

**Move File (after successful write):**
1. Rename file in place (if needed per pattern)
2. Move file to destination directory (op/ or nc/)
3. On move failure:
   - Leave file in original location with updated metadata
   - DO NOT move back (metadata is correct, location is not)
   - Log error with filename and destination
   - File marked with "move_error" in report
4. Continue processing remaining files

**Report Recording:**
```json
{
    "metadata_write_status": "success" | "failed",
    "backup_created": true | false,
    "backup_restored": true | false,
    "metadata_validated": true | false,
    "move_status": "success" | "partial" | "failed",
    "move_error": "disk full" | "permission denied" | null
}
```
```

---

### **GAP #10: Report Validation Command & Invocation**

**Plan Reference:** "Validate report correctness with deterministic checks"  
**Spec Section:** 8.3, Section 9  
**Issue:**
- Spec has validation checklist but doesn't specify:
- Is validation built-in to the tool or external?
- Should there be `--validate-report` command?
- Or Python utility script to validate any report?
- What does tool output on validation success/failure?

**Impact:** Operational detail—unclear how to perform validation  
**Recommendation:**
```
### 4.4 Report Validation

**Built-in Validation (Post-Processing):**

Add `--validate` flag:
```bash
python music_organizer.py --validate-report report.json
```

**Output (stdout):**
```
=== Report Validation ===
File: report.json
Schema version: 1.0
Records: 42
[✓] Record count in summary matches file list: 42 == 42
[✓] Routing totals: op=30 + nc=12 = 42 (matches total)
[✓] Error count: 2 (matches error_breakdown tally)
[✓] Timestamp is valid ISO8601
[✓] All error codes defined
[✗] Field mismatch: File #15 missing 'actual_filename'

Validation FAILED (1 issue found)
Exit code: 1
```

**Deterministic Checks:**
1. File count in summary == count of records in files array
2. Routing totals (op + nc) == total_files_processed
3. Error count in summary == sum of per-file error counts
4. All error codes in per-file records defined in error code registry
5. All timestamps are ISO8601 valid
6. Before/after metadata structure matches schema
7. Proposed/actual filenames consistent (proposed in dry-run, actual in apply)
8. Extension preserved in all filenames
```

---

### **GAP #11: GUI File Editor "Save" vs. "Process All" Distinction**

**Plan Reference:** "Build UI for ... saving updates, and processing all files"  
**Spec Section:** 5.2  
**Issue:**
- GUI Workflow mentions "Edit", "save metadata", "Process All"
- Unclear distinction:
  - Does "save" write to file immediately?
  - Does "Process All" batch-process all files (dry-run or apply)?
  - Are both subject to --apply flag?

**Impact:** UX specification—unclear button/action semantics  
**Recommendation:**
```
#### 5.2 GUI Workflow (Clarified)

**Button Actions:**

1. **Edit Metadata** (per file)
   - Select file → Show metadata editor dialog
   - User modifies fields in-memory
   - "Save Changes" button → Staging (NOT written to file)
   - Changes persist until "Discard" or app closes

2. **Apply Changes** (write to file)
   - Requires --apply mode or explicit "Apply Now" confirmation
   - Writes metadata to file + renames file + routes to op/nc
   - Report updated with actual outcomes

3. **Undo Changes**
   - Discard in-memory edits, revert to original file metadata

4. **Process All Files**
   - Apply batch processing with current settings
   - If --dry-run: Show preview report only
   - If --apply: Write all files, generate report
   - User prompted: "Apply changes to N files? [Yes/No]"

5. **Export / View Report**
   - Display report in GUI (table or JSON viewer)
   - Allow export to file
   - Show summary statistics

**Modes:**
- Dry-Run Mode (default): All actions are preview-only
- Apply Mode: Requires confirmation, writes files
```

---

### **GAP #12: Track Number Format Preservation**

**Plan Reference:** "Normalize track format"  
**Spec Section:** 2.1.2 (4)  
**Issue:**
- Spec normalizes track to "1" or "1/12" format
- Doesn't specify:
  - If original has "1/12", should we preserve total?
  - If original has "1" only, should we infer total from folder?
  - What if original has non-standard format like "A1" (vinyl)?

**Impact:** Data edge case—track field handling  
**Recommendation:**
```
#### 2.1.2 Track Number Normalization (Enhanced)

**Normalization Rules:**

1. **Accepted Formats (Input):**
   - "1" → Track without total
   - "01" → Pad with zero (convert to "1")
   - "1/12" or "1 / 12" → Track with total
   - "01/12" → Normalize to "1/12"
   - Non-numeric (A1, T01, etc.) → Leave as-is or error

2. **Output Format:**
   - If original had total: "track/total" (e.g., "3/12")
   - If original had no total: "track_only" (e.g., "3")
   - Strip leading zeros
   - Validate: track <= total (if both present)

3. **Preservation:**
   - Always preserve "total" field if present in original
   - Infer total from folder structure only if explicitly enabled in config
   - Report both original and normalized track in before/after metadata

**Example:**
```
Original: "01" → Normalized: "1"
Original: "03/15" → Normalized: "3/15"
Original: "track 5" → Left as-is or error (non-numeric)
```
```

---

### **GAP #13: Missing Metadata Second-Pass Behavior**

**Plan Reference:** "Route missing-metadata follow-up workflow to read files from `music/nc`"  
**Spec Section:** 2.3.3  
**Issue:**
- Spec defines --source-nc flag for second pass
- Doesn't clarify:
  - Can first pass be --apply? (Or must it be dry-run to preserve files in nc/?)
  - If first pass is --apply and moves files to nc/, can second pass automatically --apply?
  - What if second pass patches still leave metadata missing?

**Impact:** Workflow ambiguity—unclear operational sequence  
**Recommendation:**
```
#### 2.3.3 Missing Metadata Follow-up Workflow (Clarified)

**Recommended Workflow:**

**Pass 1: Initial Processing**
```bash
python music_organizer.py music/ip --apply
# Result: op/ has renamed files, nc/ has missing-metadata files
```

**Pass 2: Metadata Supply & Follow-up**
```bash
python music_organizer.py \
  --source-nc \
  --metadata-json missing_metadata.json \
  --apply
# Input: files from music/nc
# Apply patches from JSON
# Output: op/ (if metadata resolved) or nc/ (if still missing)
```

**Edge Cases:**

1. **Second pass still missing metadata:**
   - Files remain in nc/
   - Routing marked as "partial" or "needs_manual_review"
   - Report notes which fields are still missing

2. **Second pass no metadata supplied:**
   - Files re-process according to fallback rules
   - May move to op/ if fallback succeeds now, or stay in nc/

3. **Idempotent guarantee:**
   - Running same command twice should produce same result
   - Files already in op/ should not be re-processed
   - Files in nc/ re-processed only if --source-nc flag set

**Force Flag (Optional):**
Add `--force-reprocess` to allow reprocessing files in op/
(dangerous—could cause unintended renames)
```

---

### **GAP #14: Report Schema Versioning & Stability**

**Plan Reference:** "Keep report schema stable for automated validation"  
**Spec Section:** 3.2  
**Issue:**
- Spec defines schema version "1.0"
- Doesn't specify:
  - Backward compatibility policy
  - How to indicate breaking changes
  - Migration path for consumers of reports
  - Deprecation policy for fields

**Impact:** Long-term maintenance—unclear evolution strategy  
**Recommendation:**
```
### Report Schema Versioning Policy

**Versioning:**
- Format: MAJOR.MINOR
- MAJOR: Breaking changes (new required fields, removed fields)
- MINOR: Backward-compatible additions (new optional fields)
- Example: 1.0 → 1.1 (added optional field) → 2.0 (removed field)

**Stability Guarantees:**

1. **v1.x Fields** (permanent):
   - metadata.version, timestamp, input_folder, pattern, dry_run
   - files[].original_filename, original_metadata, cleaned_metadata
   - files[].proposed_filename, actual_filename
   - files[].proposed_routing, actual_routing
   - files[].errors
   - summary.total_files_processed, routed_to_op, routed_to_nc, total_errors

2. **Allowed Additions (minor version bump):**
   - New optional fields in files[] objects
   - New keys in error.context (for additional context)
   - New metadata fields (but only if ISO 639 tags or standard)

3. **Breaking Changes (major version bump):**
   - Rename existing fields
   - Remove fields
   - Change error code values
   - Restructure summary object

**Example (Future):**
```json
{
  "metadata": {
    "version": "1.1",
    "timestamp": "...",
    ...
    "total_duration_seconds": 1234  // New optional field in v1.1
  }
}
```

**Deprecation:**
- Deprecated fields marked with `_deprecated` suffix
- Still populated but consumers should migrate
- Removed in next major version (e.g., v1.5 → v2.0)
```

---

### **GAP #15: Configuration File Search & Loading Order**

**Plan Reference:** Configuration file support (implicit)  
**Spec Section:** 4.2  
**Issue:**
- Spec mentions "YAML format at `configs/music_organizer_config.yaml`"
- Doesn't specify:
  - Where should config file be searched? (cwd, home dir, module dir?)
  - Priority when multiple configs exist?
  - Fallback behavior if config file missing?
  - How to validate config YAML?

**Impact:** Deployment detail—unclear configuration precedence  
**Recommendation:**
```
### Configuration File Resolution

**Search Order (first found wins):**
1. `--config FILE` (CLI argument, highest priority)
2. `./music_organizer_config.yaml` (current working directory)
3. `~/.config/music_organizer/config.yaml` (user home)
4. `/etc/music_organizer/config.yaml` (system, Linux/Mac only)
5. Built-in defaults (hardcoded, lowest priority)

**YAML Validation:**
- Schema validation against predefined structure
- Required keys: (none—all optional, fallback to defaults)
- Optional keys: noise_words, default_pattern, default_music_root, etc.
- On schema validation error: Log warning, use defaults, continue

**Example Config:**
```yaml
# music_organizer_config.yaml
noise_words:
  - Remastered
  - Deluxe Edition
  - Album Version

default_pattern: "{artist}/{album}/{track} - {title}"
default_music_root: "~/Music"
default_report_file: "~/Music/reports/latest.json"
log_level: INFO
filename_sanitize_strategy: "replace"
symlink_follow: false
```

**CLI Override:**
- CLI arguments always override config file settings
- Example: `--pattern X` overrides config default_pattern
```

---

## Summary Table

| Gap # | Category | Severity | Type | Required Before Implementation? |
|-------|----------|----------|------|--------------------------------|
| 1 | Logging Architecture | Medium | Operational | Yes (for actionable logs) |
| 2 | Console Output Display | Medium | UX | Yes (for user feedback) |
| 3 | Default Noise Words | Low | Configuration | Yes (for domain rules) |
| 4 | Dry-Run Report Behavior | Medium | Workflow | Yes (for predictability) |
| 5 | Routing Distinction | High | Workflow | Yes (affects directory structure) |
| 6 | Collision Resolution | Medium | Algorithm | Yes (for determinism) |
| 7 | Filename Sanitization | Medium | Cross-platform | Yes (for filesystem safety) |
| 8 | Fallback Priority | High | Data Integrity | Yes (for predictable behavior) |
| 9 | Move Error Recovery | Medium | Safety | Yes (for data protection) |
| 10 | Validation Invocation | Low | Operational | No (can defer, add later) |
| 11 | GUI Edit/Process Semantics | High | UX | Yes (if implementing GUI) |
| 12 | Track Format Handling | Low | Edge Case | No (can use simple rule) |
| 13 | Multi-Pass Workflow | Medium | Operational | Yes (for two-pass workflow) |
| 14 | Schema Versioning | Low | Long-term | No (can defer to v2.0) |
| 15 | Config File Resolution | Low | Deployment | No (can use simple search) |

---

## Recommendations for Implementation

### **Critical Gaps (Must Fix Before Code):**
- **Gap #5**: Clarify routing rules (complete decision tree)
- **Gap #8**: Define fallback priority (data merge strategy)
- **Gap #1**: Specify logging system (log format, levels, destinations)

### **Important Gaps (Fix Before Public Release):**
- **Gap #2**: Specify console output format (user feedback)
- **Gap #4**: Define dry-run report behavior (workflow predictability)
- **Gap #7**: Define filename sanitization rules (cross-platform safety)
- **Gap #9**: Define move error recovery (data protection)
- **Gap #11**: Clarify GUI semantics (if building GUI)

### **Nice-to-Have Gaps (Can Defer or Doc Later):**
- **Gap #3**: Document noise word defaults (reference list)
- **Gap #6**: Document collision resolution examples
- **Gap #10**: Implement validation command (future enhancement)
- **Gap #12**: Document track format edge cases
- **Gap #13**: Document recommended workflow sequences
- **Gap #14**: Plan schema versioning policy (v2.0 planning)
- **Gap #15**: Document config file search order

---

## Next Steps

1. **Create Implementation Guide** addressing all critical gaps
2. **Review CLI Test Cases** with clarified routing and fallback logic
3. **Define Default Configuration** (noise words, patterns, sanitization)
4. **Update Spec Sections** with clarifications from this report
5. **Begin Implementation Phase 1** (Core Metadata Pipeline)

---

## Appendix: Quick Reference Checklist

- [ ] Logging system (format, levels, output)
- [ ] Console output format (print metadata blocks)
- [ ] Default noise words list
- [ ] Dry-run report file behavior
- [ ] Routing decision tree (complete)
- [ ] Collision resolution algorithm (numeric suffix strategy)
- [ ] Filename sanitization rules (per-platform)
- [ ] Fallback priority order (sources ranked)
- [ ] File move error recovery (what to do if move fails)
- [ ] Report validation command (`--validate-report`)
- [ ] GUI Edit/Process distinctions (if GUI required)
- [ ] Track number format rules (normalize strategy)
- [ ] Multi-pass workflow sequence (Pass 1 & Pass 2)
- [ ] Schema versioning policy (backward compatibility)
- [ ] Config file search order (precedence)

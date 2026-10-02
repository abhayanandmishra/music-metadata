# Music Organizer Specification

**Version:** 1.0  
**Date:** 2026-09-30  
**Status:** Draft

---

## 1. System Overview

The Music Organizer is a Python tool that processes music files one-by-one to:
- Extract and clean metadata (artist, title, album, track, genre, year)
- Apply domain-specific normalization rules
- Handle missing metadata via fallback and external input processes
- Write cleaned metadata back to files safely
- Rename files using customizable patterns
- Route files to appropriate directories based on metadata state
- Generate comprehensive reports with validation support

**Supported Formats:** MP3, FLAC, M4A, AAC, OGG, OPUS, WAV, WMA (via mutagen library)

---

## 2. Detailed Functional Requirements

### 2.1 Metadata Processing Pipeline

#### 2.1.1 Read Metadata
- Iterate through music files one-at-a-time from input directory
- Use mutagen library with easy tags API to extract:
  - Artist (`artist`)
  - Title (`title`)
  - Album (`album`)
  - Track Number (`track`)
  - Genre (`genre`)
  - Year (`date`)
  - Original filename stem (parsed from file path)
- Store original metadata state for before/after reporting

#### 2.1.2 Clean Metadata
Apply the following normalizations in order:

1. **Whitespace Cleanup**
   - Strip leading/trailing whitespace from all fields
   - Collapse internal multiple spaces to single space

2. **Noise Word Removal**
   - Define a configurable list of noise words (e.g., "Remastered", "Deluxe Edition", "Album Version")
   - Remove noise words from album and title fields
   - Use case-insensitive matching with word boundary detection

3. **Album Rule: Remove Year Tokens**
   - Detect and remove year patterns (e.g., "Album (2020)", "Album - 2020") from album field
   - Preserve year in the `year`/`date` field

4. **Track Number Normalization**
   - Normalize track format to integer or "N/M" format (track/total)
   - Handle inputs like "01", "1/12", "01/12", "1 / 12"
   - Output normalized as "1" or "1/12"

5. **Separator Normalization**
   - Normalize separators in artist/album/title (standardize various dashes to hyphen)

#### 2.1.3 Missing Metadata Fallback
When any critical field (artist, title, album) is missing or empty:

1. **Filename Parsing**
   - Parse filename stem into segments (split by common delimiters: `-`, `_`, ` `)
   - Attempt to infer title from filename segments
   - Use first segment as fallback for artist/album if available

2. **Parent Folder Hints**
   - Check parent folder name for artist/album patterns
   - Apply heuristics (e.g., if folder matches artist pattern, use as artist hint)

3. **External Metadata Input**
   - Accept metadata patches via:
     - JSON file (`--metadata-json FILE`)
     - Inline JSON (`--metadata-inline-json JSON_STRING`)
   - Format: `{"filename_or_stem": {"field": "value", ...}, ...}`
   - **Only fill missing fields** (non-destructive merge)

#### 2.1.4 Write Metadata Safely
- Create backup of original file before writing
- Write cleaned tags back to file using mutagen
- Validate output file:
  - File size > 0
  - File readable and tag-parseable
- On validation failure: restore from backup and log error
- Handle corruption scenarios gracefully

### 2.2 File Renaming

#### 2.2.1 Rename Pattern
- Default pattern: `{album} - {title}`
- Configurable via `--pattern` CLI argument
- Support placeholder fields: `{artist}`, `{album}`, `{title}`, `{track}`, `{genre}`, `{year}`, `{original_filename}`
- Preserve file extension from original file
- Sanitize filename (remove/replace invalid filesystem characters)

#### 2.2.2 Collision Handling
- Check for rename collisions (target filename already exists)
- If collision detected: append suffix (e.g., `filename_1.mp3`, `filename_2.mp3`)
- Log collision along with resolution strategy

### 2.3 Directory Workflow

#### 2.3.1 Directory Structure
```
music/
├── ip/                    # Input folder (read source files)
├── op/                    # Output folder (successfully processed files)
└── nc/                    # No-change / No-metadata folder (missing metadata backlog)
```

#### 2.3.2 Routing Rules
- **To `op/`**: Files successfully cleaned and renamed
- **To `nc/`**: Files with unresolved missing metadata after fallback process
- **Logical only in dry-run**: During `--apply`, physically move files

#### 2.3.3 Missing Metadata Follow-up Workflow
- Second pass: Read from `music/nc`
- Accept metadata patches via CLI/JSON
- Apply patches (only missing fields)
- Attempt rename and move to `op/`
- Route unresolved files back to `nc/`
- Use `--source-nc` flag to read from `music/nc` instead of `music/ip`

### 2.4 Dry-Run and Apply Modes

#### 2.4.1 Dry-Run Mode (Default)
- Parse and clean metadata without writing
- Show proposed renames and moves
- Generate report with proposed changes (no actual file modifications)
- Exit with success (0) or error code for failures
- **Default behavior**: `python music_organizer.py` runs in dry-run

#### 2.4.2 Apply Mode
- Require explicit `--apply` flag
- Write cleaned metadata to files
- Perform actual file renames and moves
- Update report to reflect actual outcomes

### 2.5 Error Handling

#### 2.5.1 Error Categories
- **Unsupported format**: File type not in supported list
- **Unreadable file**: File cannot be read (permissions, corruption)
- **Write failure**: Cannot write metadata (file in use, permission denied)
- **Rename collision**: Target filename exists
- **Filesystem error**: Cannot move file to target directory
- **Validation error**: Post-write file validation fails

#### 2.5.2 Error Response
- Log error with context (file, cause, action taken)
- Continue processing remaining files
- Store error in per-file report entry
- Increment error counter in summary

### 2.6 Report Generation

#### 2.6.1 Report Format
- JSON format (utf-8 encoded)
- Default output: `music/music_organizer_report.json`
- Configurable via `--report-file` argument
- Generated automatically (enabled by default)

#### 2.6.2 Report Contents
- **Metadata**: Per-file original and cleaned metadata
- **Rename Outcome**: Original filename → new filename (or reason for no rename)
- **Routing**: Proposed/actual directory move (`op` or `nc`)
- **Errors**: Per-file error list with error code, message, context
- **Summary**: File counts, routing breakdown, error tally

---

## 3. Data Models

### 3.1 Metadata Record (In-Memory)
```python
{
    "original_filename": str,
    "original_metadata": {
        "artist": str or None,
        "title": str or None,
        "album": str or None,
        "track": str or int or None,
        "genre": str or None,
        "year": str or int or None
    },
    "cleaned_metadata": {
        "artist": str or None,
        "title": str or None,
        "album": str or None,
        "track": str or int or None,
        "genre": str or None,
        "year": str or int or None
    },
    "fallback_applied": bool,
    "external_metadata_applied": bool,
    "proposed_filename": str or None,
    "actual_filename": str or None,
    "proposed_routing": "op" | "nc",
    "actual_routing": "op" | "nc",
    "errors": [
        {
            "code": str,
            "message": str,
            "context": dict
        }
    ]
}
```

### 3.2 Report Schema (JSON Output)
```json
{
    "metadata": {
        "version": "1.0",
        "timestamp": "ISO8601",
        "input_folder": "string",
        "music_root": "string",
        "pattern": "string",
        "dry_run": bool,
        "source_nc": bool
    },
    "files": [
        {
            "original_filename": "string",
            "original_metadata": {
                "artist": "string or null",
                "title": "string or null",
                "album": "string or null",
                "track": "string or null",
                "genre": "string or null",
                "year": "string or null"
            },
            "cleaned_metadata": {
                "artist": "string or null",
                "title": "string or null",
                "album": "string or null",
                "track": "string or null",
                "genre": "string or null",
                "year": "string or null"
            },
            "fallback_applied": bool,
            "external_metadata_applied": bool,
            "proposed_filename": "string or null",
            "actual_filename": "string or null",
            "proposed_routing": "op" | "nc",
            "actual_routing": "op" | "nc",
            "errors": [
                {
                    "code": "string",
                    "message": "string",
                    "context": {}
                }
            ]
        }
    ],
    "summary": {
        "total_files_processed": int,
        "successful_renames": int,
        "routed_to_op": int,
        "routed_to_nc": int,
        "total_errors": int,
        "error_breakdown": {
            "error_code": int
        }
    }
}
```

---

## 4. API & Configuration

### 4.1 CLI Interface

```bash
python music_organizer.py [folder] [options]
```

**Positional Arguments:**
- `folder`: Input folder. Default: `music/ip`

**Options:**
- `-h, --help`: Show help message
- `--pattern PATTERN`: Rename pattern. Default: `{album} - {title}`
- `--dry-run`: Preview mode (default behavior)
- `--apply`: Actually apply changes
- `--no-write-metadata`: Skip writing tags to files
- `--metadata-json FILE`: Path to JSON metadata patch file
- `--metadata-inline-json JSON`: Inline JSON metadata patch
- `--report-file FILE`: Output report path. Default: `music/music_organizer_report.json`
- `--music-root DIR`: Root folder containing `ip`, `op`, `nc`. Default: `music`
- `--source-nc`: Read from `music/nc` instead of `music/ip`

### 4.2 Configuration File (Optional)
- YAML format at `configs/music_organizer_config.yaml`
- Settings override CLI defaults
- Include noise words list, domain rules, default pattern

### 4.3 Metadata Patch JSON Format

**File Input (`--metadata-json`):**
```json
{
    "song_name.mp3": {
        "artist": "Artist Name",
        "album": "Album Name"
    },
    "another_song": {
        "title": "Song Title"
    }
}
```

**Inline Input (`--metadata-inline-json`):**
```bash
--metadata-inline-json '{"filename": {"field": "value"}}'
```

**Matching Strategy:**
1. Exact filename match
2. Filename stem match (without extension)
3. Relative path match

---

## 5. Workflow & User Interactions

### 5.1 CLI Workflow (Batch Processing)
1. Parse CLI arguments
2. Load configuration
3. Validate input folder exists
4. Scan for supported music files
5. For each file:
   - Read metadata
   - Clean metadata
   - Apply fallback if needed
   - Apply external patches if needed
   - Determine rename and routing
6. Generate report
7. If `--apply`: write metadata, perform renames, move files
8. Output report and summary

### 5.2 GUI Workflow (Interactive)
1. Start application
2. Select input folder (or use default `music/ip`)
3. Scan for music files (displays file list)
4. User can:
   - **Edit**: Select file, click edit, modify metadata fields, save
   - **Search/Filter**: Type in search box to filter file list by filename/metadata
   - **Process All**: Process all files with current settings (respects dry-run/apply)
   - **Dry-Run Preview**: Show proposed changes before applying
5. Generate and display report

---

## 6. Milestone Plan

### Phase 1: Core Metadata Pipeline (Week 1-2)
- [ ] Implement file scanner for supported formats
- [ ] Build metadata read functionality (mutagen integration)
- [ ] Implement metadata cleaning (whitespace, noise words, year removal, track normalization)
- [ ] Unit tests for metadata cleaning edge cases
- [ ] Fallback inference from filename/folder

### Phase 2: Write & Rename (Week 2-3)
- [ ] Implement safe write with backup/restore
- [ ] Implement file validation post-write
- [ ] Implement rename pattern system
- [ ] Implement collision detection and resolution
- [ ] Unit tests for write, rename, collision scenarios

### Phase 3: Directory Workflow & Routing (Week 3-4)
- [ ] Implement directory structure setup (`ip`, `op`, `nc`)
- [ ] Implement routing logic
- [ ] Implement file move operations
- [ ] Unit tests for routing logic

### Phase 4: Report Generation & Validation (Week 4-5)
- [ ] Implement report schema (JSON)
- [ ] Implement per-file record building
- [ ] Implement summary calculations
- [ ] Implement report validation (record counts, error tally)
- [ ] Unit tests for report generation and validation

### Phase 5: External Metadata Input (Week 5-6)
- [ ] Implement JSON file metadata input
- [ ] Implement inline JSON metadata input
- [ ] Implement matching strategy (filename, stem, path)
- [ ] Implement non-destructive merge
- [ ] Unit tests for metadata patching

### Phase 6: Dry-Run & Apply Modes (Week 6-7)
- [ ] Implement dry-run logic (no file modifications)
- [ ] Implement apply mode with file operations
- [ ] CLI argument parsing and validation
- [ ] Integration tests for both modes

### Phase 7: CLI & Configuration (Week 7-8)
- [ ] Implement CLI argument parser
- [ ] Implement configuration file loading (YAML)
- [ ] Implement default overrides
- [ ] CLI help and usage documentation

### Phase 8: GUI (Week 8-10)
- [ ] Design GUI layout (folder selector, file list, metadata editor, apply buttons)
- [ ] Implement folder selection dialog
- [ ] Implement file listing and display
- [ ] Implement metadata editor with live preview
- [ ] Implement search/filter functionality
- [ ] Implement process buttons (dry-run, apply)
- [ ] Implement report viewer

### Phase 9: Error Handling & Robustness (Week 10-11)
- [ ] Comprehensive error handling across all modules
- [ ] Error logging and context
- [ ] Graceful degradation
- [ ] Permission and access error handling
- [ ] Integration tests for error scenarios

### Phase 10: Testing & Validation (Week 11-12)
- [ ] Complete test suite (unit + integration)
- [ ] Validation checklist execution
- [ ] Performance testing with large file sets
- [ ] Edge case testing
- [ ] Documentation

---

## 7. Risk & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Metadata write corruption | HIGH | Implement backup/restore with post-write validation. Test with corrupted test files. Use mutagen safely_write. |
| File permission issues | MEDIUM | Check file permissions before operations. Gracefully handle permission denied errors. Provide clear error messages. |
| Filename collision | MEDIUM | Implement collision detection with numeric suffix. Log all collisions. Provide user preview before apply. |
| Missing metadata leads to unusable output | MEDIUM | Implement fallback inference. Provide external metadata input mechanism. Route unresolved to `nc/`. |
| Large file sets cause memory issues | MEDIUM | Process files one-at-a-time (streaming approach). Implement batch processing with memory management. |
| Character encoding in metadata | MEDIUM | Standardize on UTF-8. Handle encoding errors in mutagen. Sanitize filenames for filesystem. |
| Report validation false negatives | MEDIUM | Define deterministic validation checks. Include before/after metadata in report for manual verification. |
| GUI responsiveness with large file sets | LOW | Implement async file scanning. Use background thread for processing. Update GUI incrementally. |
| External metadata JSON large file handling | LOW | Stream JSON parsing. Implement size limits and warnings. Validate JSON early. |
| Year token removal too aggressive | LOW | Use careful regex with word boundaries. Include year in output report for manual verification. |

---

## 8. Validation Checklist

### 8.1 Dry-Run Validation
- [ ] Metadata cleaning produces expected output for all test cases
- [ ] Fallback inference fills missing fields correctly
- [ ] Rename pattern generates valid filenames
- [ ] Collision detection identifies duplicates
- [ ] Routing logic (op/nc) assigns files correctly
- [ ] Report generated with all required fields
- [ ] No files modified (dry-run promise)
- [ ] Error messages are clear and actionable

### 8.2 Apply Run Validation
- [ ] Metadata written to files (verify with tag reader)
- [ ] Files renamed correctly
- [ ] Files moved to correct directories
- [ ] Backup files cleaned up after successful write
- [ ] Backup files restored on write failure
- [ ] Collisions resolved with numeric suffix
- [ ] Report reflects actual outcomes (not proposed)
- [ ] No data loss occurred

### 8.3 Report Validation
- [ ] Record count matches actual files processed
- [ ] Summary totals are consistent (op + nc + errors = total)
- [ ] Error count matches errors in per-file records
- [ ] Error codes are defined and consistent
- [ ] Before/after metadata is populated correctly
- [ ] Routing destinations are valid (op or nc)
- [ ] Timestamp is ISO8601 and correct
- [ ] Report is valid JSON and parseable

### 8.4 End-to-End Scenarios
- [ ] Process files with complete metadata → renamed to op/
- [ ] Process files with missing metadata (no external input) → routed to nc/
- [ ] Process files with external metadata patches → missing fields filled, renamed to op/
- [ ] Handle unsupported file format → logged as error, routed to nc/
- [ ] Handle unreadable file (permissions) → logged as error, routed to nc/
- [ ] Handle write failure (file in use) → backed up, restored, logged as error
- [ ] Handle rename collision → suffix appended, logged
- [ ] Run second pass from nc/ with external metadata → successfully renames and moves

---

## 9. Test Plan

### 9.1 Unit Tests

#### 9.1.1 Metadata Cleaning Tests
```python
def test_strip_whitespace():
    # Input: "  Artist  Name  "
    # Expected: "Artist Name"
    pass

def test_remove_noise_words():
    # Input album: "Album Name (Remastered Edition)"
    # Expected: "Album Name"
    pass

def test_remove_year_from_album():
    # Input: "Album - 2020", "Album (2020)", "Album 2020"
    # Expected: "Album" for all variants
    pass

def test_normalize_track_number():
    # Test cases: "01", "1/12", "1 / 12", "01/12"
    # Expected: "1" or "1/12"
    pass

def test_handle_empty_fields():
    # Input: artist=None, title="", album=None
    # Expected: fallback triggered or fields remain None
    pass
```

#### 9.1.2 Fallback Inference Tests
```python
def test_infer_from_filename():
    # Filename: "artist_name-song_title"
    # Expected: infer artist and title from segments
    pass

def test_infer_from_parent_folder():
    # Folder: "music/Artist Name"
    # Expected: infer artist from folder
    pass

def test_fallback_with_filename_and_folder():
    # Validate fallback order and heuristics
    pass
```

#### 9.1.3 Rename Pattern Tests
```python
def test_rename_with_default_pattern():
    # Input: album="Album", title="Song"
    # Pattern: "{album} - {title}"
    # Expected: "Album - Song.mp3"
    pass

def test_rename_with_custom_pattern():
    # Input: artist="Artist", album="Album", title="Song"
    # Pattern: "{artist}/{album}/{title}"
    # Expected: "Artist/Album/Song.mp3"
    pass

def test_sanitize_invalid_chars():
    # Input: title="Song: The Best * Ever?"
    # Expected: "Song The Best Ever.mp3" (invalid chars removed/replaced)
    pass
```

#### 9.1.4 Collision Detection Tests
```python
def test_detect_collision():
    # Files in op/: "Song.mp3"
    # New rename: "Song.mp3"
    # Expected: collision detected, suffix appended
    pass

def test_resolve_collision_suffix():
    # Input: "Song.mp3" (exists), "Song_1.mp3" (exists)
    # Expected: new file gets "Song_2.mp3"
    pass
```

#### 9.1.5 External Metadata Patch Tests
```python
def test_apply_metadata_patch_file():
    # Patch: {"song.mp3": {"artist": "New Artist"}}
    # Input metadata: artist=None, title="Song"
    # Expected: artist="New Artist", title="Song" (title preserved)
    pass

def test_apply_inline_json_patch():
    # Inline: {"song": {"album": "Album Name"}}
    # Expected: album filled, other fields preserved
    pass

def test_non_destructive_merge():
    # Existing metadata has artist, patch has title
    # Expected: both preserved, no overwrites
    pass
```

#### 9.1.6 Write Safety Tests
```python
def test_backup_before_write():
    # Write operation should create backup
    # Expected: backup file exists
    pass

def test_restore_on_validation_failure():
    # Write metadata, validation fails
    # Expected: original file restored from backup
    pass

def test_file_size_validation():
    # Write operations should validate output size > 0
    # Expected: validation caught empty file
    pass
```

#### 9.1.7 Report Generation Tests
```python
def test_report_schema_valid():
    # Generate report for sample files
    # Expected: report matches schema (valid JSON, required fields)
    pass

def test_report_summary_accuracy():
    # Process 5 files: 3 to op/, 2 to nc/
    # Expected: summary totals match (total=5, op=3, nc=2)
    pass

def test_report_error_tally():
    # Process files with errors
    # Expected: error count in summary matches per-file error counts
    pass
```

### 9.2 Integration Tests

#### 9.2.1 End-to-End Dry-Run
```python
def test_e2e_dry_run_complete_metadata():
    # Input: 3 files with complete metadata
    # Expected: rename proposed, routed to op/, no modifications
    pass

def test_e2e_dry_run_missing_metadata():
    # Input: 2 files with missing artist/album
    # Expected: fallback attempted, routed to op/ or nc/
    pass

def test_e2e_dry_run_mixed():
    # Input: mix of complete, missing, unsupported files
    # Expected: correct routing and error logging
    pass
```

#### 9.2.2 End-to-End Apply
```python
def test_e2e_apply_successful():
    # Input: files with metadata
    # Apply: --apply flag
    # Expected: files renamed, moved to op/, metadata written
    pass

def test_e2e_apply_with_collisions():
    # Input: files that would have same rename output
    # Apply: --apply flag
    # Expected: collisions resolved with suffix, files moved
    pass

def test_e2e_apply_with_errors():
    # Input: mix of valid and invalid files
    # Apply: --apply flag
    # Expected: valid files processed, errors logged, continue processing
    pass
```

#### 9.2.3 Missing Metadata Follow-up
```python
def test_e2e_follow_up_from_nc():
    # First pass: files without metadata → nc/
    # Second pass: --source-nc with metadata patches
    # Expected: files filled with metadata, moved to op/
    pass

def test_e2e_follow_up_still_missing():
    # First pass: files without metadata → nc/
    # Second pass: patches provided but incomplete
    # Expected: files remain in nc/ (or re-routed if ambiguous)
    pass
```

#### 9.2.4 External Metadata Input
```python
def test_cli_with_metadata_json():
    # Input: --metadata-json patches.json
    # Expected: patches applied, non-missing fields preserved
    pass

def test_cli_with_inline_json():
    # Input: --metadata-inline-json '{"file": {"artist": "X"}}'
    # Expected: patches applied correctly
    pass
```

### 9.3 Edge Case Tests

#### 9.3.1 Special Characters & Encoding
```python
def test_metadata_with_unicode():
    # Input: artist="Björk", title="Ísafold"
    # Expected: metadata preserved, filename sanitized for filesystem
    pass

def test_filename_with_special_chars():
    # Input: "Song: The Best * Ever?.mp3"
    # Expected: special chars handled, renamed safely
    pass

def test_metadata_with_quotes_and_apostrophes():
    # Input: title="It's the 'Best' Song"
    # Expected: preserved or escaped correctly
    pass
```

#### 9.3.2 Boundary Conditions
```python
def test_empty_input_folder():
    # Input: empty folder
    # Expected: process completes, report shows 0 files
    pass

def test_very_large_filename():
    # Input: filename > 255 chars (filesystem limit)
    # Expected: truncated safely or error logged
    pass

def test_deeply_nested_folder_structure():
    # Input: files in deep subfolders
    # Expected: all files found and processed
    pass

def test_symlink_handling():
    # Input: music files accessed via symlinks
    # Expected: handled correctly or logged appropriately
    pass
```

#### 9.3.3 Concurrency & Performance
```python
def test_process_1000_files():
    # Input: 1000 media files in input folder
    # Expected: all processed, no memory issues
    pass

def test_large_report_generation():
    # Input: 5000 files processed
    # Expected: report generated without timeouts
    pass
```

### 9.4 Error Scenario Tests

#### 9.4.1 File System Errors
```python
def test_file_permission_denied():
    # Input: read-only file
    # Expected: error logged, continue processing
    pass

def test_disk_full_on_rename():
    # Simulate: no space for backup/write
    # Expected: error logged, file routed to nc/, process continues
    pass

def test_file_in_use_on_write():
    # Simulate: file locked by another process
    # Expected: error logged, continue processing
    pass
```

#### 9.4.2 Metadata & Format Errors
```python
def test_corrupted_tag_data():
    # Input: file with corrupt tags
    # Expected: error logged, fallback attempted
    pass

def test_unsupported_format():
    # Input: .flv or other unsupported file
    # Expected: skipped, error logged
    pass

def test_zero_duration_file():
    # Input: empty or invalid media file
    # Expected: handled gracefully
    pass
```

#### 9.4.3 Input Validation Errors
```python
def test_invalid_metadata_json():
    # Input: --metadata-json with malformed JSON
    # Expected: clear error message, graceful exit
    pass

def test_invalid_pattern():
    # Input: --pattern with invalid placeholders
    # Expected: error message, use default pattern
    pass

def test_missing_root_folder():
    # Input: --music-root pointing to non-existent folder
    # Expected: error or auto-create with warning
    pass
```

### 9.5 Test Data

**Sample Test Files:**
- `test_data/complete_metadata.mp3`: All fields populated
- `test_data/missing_artist.mp3`: Artist field empty
- `test_data/missing_album_title.mp3`: Multiple missing fields
- `test_data/noise_album.mp3`: Album contains noise words
- `test_data/with_year_in_album.mp3`: Album field includes year
- `test_data/unicode_metadata.mp3`: International characters in artist/title
- `test_data/special_chars_filename.mp3`: Invalid filesystem characters in original filename
- `test_data/corrupted_tags.mp3`: Invalid or corrupted metadata tags

**Sample Test Patches:**
- `test_data/patches_complete.json`: Full metadata for multiple files
- `test_data/patches_partial.json`: Partial metadata (only missing fields)
- `test_data/patches_invalid.json`: Malformed JSON or invalid formats

---

## 10. Non-Functional Requirements

### 10.1 Reliability
- **No Data Loss**: Original files preserved until write validated
- **Corruption Protection**: Backup/restore mechanism for failed writes
- **Error Recovery**: Graceful continuation on file errors
- **Idempotence**: Running twice with same input should produce same output

### 10.2 Performance
- **One-at-a-time Processing**: Each file processed sequentially (no concurrent writes to same file)
- **Memory Efficiency**: Stream processing, not loading entire file set into memory
- **Scalability**: Support 1000+ files with reasonable runtime (<5 min for 1000 files)

### 10.3 Maintainability
- **Clear Logging**: Actionable, context-rich log messages
- **Modular Design**: Separate concerns (read, clean, write, rename, route)
- **Configuration**: Externalize noise words, patterns, and defaults

### 10.4 Usability
- **Dry-Run by Default**: Safe preview before changes
- **Clear Output**: Report with before/after metadata for verification
- **Help & Docs**: CLI help, README, inline documentation

### 10.5 Stability
- **Extension Preservation**: Rename maintains original file extension
- **Predictable Behavior**: Documented rules for all decisions
- **Validation**: Report deterministically validates using counts and summaries

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| **Metadata** | ID3 tags (or equivalent) in music files: artist, title, album, track, genre, year |
| **Noise Words** | Common suffixes/annotations in albums (e.g., "Remastered", "Deluxe Edition") |
| **Fallback** | Process to infer missing metadata from filename or folder hints |
| **Pattern** | Template string for renaming files (e.g., `{album} - {title}`) |
| **Dry-Run** | Preview mode—show changes without modifying files |
| **Apply** | Execution mode—actually modify files, write metadata, rename, and move |
| **Collision** | Two files would rename to the same filename |
| **Routing** | Logic to move processed files to `op/` or `nc/` based on metadata state |
| **Report** | JSON output documenting all processing results and errors |
| **Patch** | External metadata (JSON) supplied to fill missing fields |

---

## 12. References

- **Planning Prompt**: [planning.prompt.md](planning.prompt.md)
- **Implementation Prompt**: [implementation.prompt.md](implementation.prompt.md)
- **README**: [README.md](README.md)
- **Mutagen Documentation**: https://mutagen.readthedocs.io/

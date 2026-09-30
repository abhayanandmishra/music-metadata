# Music Renamer

This Python tool organizes music files by cleaning metadata, writing cleaned tags back into files, and renaming files with a metadata-based pattern.

## Features

- Reads metadata from common music formats: MP3, FLAC, M4A, AAC, OGG, OPUS, WAV, WMA
- Processes files one-by-one
- Cleans metadata and removes noise words
- Applies rules such as removing year from album fields
- Fills missing metadata from filename and folder hints
- Writes cleaned metadata back safely with backup/restore behavior
- Renames files using a custom pattern (default: `{album} - {title}`)
- Uses dry-run by default and requires `--apply` for actual changes
- GUI supports file listing, editable metadata, save/update, and search/filter
- Organizes files into `music/ip` (input), `music/op` (processed output), and `music/nc` (no-change / unresolved)
- Generates a JSON report by default and supports report validation

## Example

```bash
python music_organizer.py
```

Default CLI input folder is `music/ip`.

## Command Options

Usage:

```bash
python music_organizer.py [folder] [options]
```

Positional argument:

- `folder`: Folder containing music files. Default: `music/ip`

Options:

- `-h`, `--help`: Show help message and exit.
- `--pattern PATTERN`: Naming pattern for generated file names. Default: `{album} - {title}`.
- `--dry-run`: Show updates and routing plan without changing files (explicit preview flag).
- `--apply`: Apply metadata updates and move files to `op`/`nc`.
- `--no-write-metadata`: Do not write cleaned tags back to files.
- `--metadata-json METADATA_JSON`: Path to JSON metadata patch file keyed by filename/stem/path.
- `--metadata-inline-json METADATA_INLINE_JSON`: Inline JSON metadata patch object.
- `--report-file REPORT_FILE`: Output JSON report path. Default: `music/music_organizer_report.json`.
- `--music-root MUSIC_ROOT`: Root folder containing `ip`, `op`, `nc`. Default: `music`.
- `--source-nc`: Read input from `music/nc` for missing-metadata follow-up workflow.
- `--validate-report VALIDATE_REPORT`: Validate an existing report file and exit.

Notes:

- Running without `--apply` is preview mode and does not change files.
- `--apply --dry-run` still behaves as dry-run (preview only).
- Metadata patches from `--metadata-json` and `--metadata-inline-json` fill missing fields only.

Available placeholders:

- `{artist}`
- `{title}`
- `{album}`
- `{track}`
- `{genre}`
- `{year}`
- `{original}`

Dry run example:

```bash
python music_organizer.py --pattern "{album} - {track} - {title}"
```

Sample dry-run output:

```text
--- Tera Mera Rishta Continues (Film Ballad) - RaagTune.mp3 ---
  Artist  : (not available)
  Title   : (not available)
  Album   : (not available)
  Track   : (not available)
  Genre   : (not available)
  Year    : (not available)
  Original: Tera Mera Rishta Continues (Film Ballad) - RaagTune
  Would rename: Tera Mera Rishta Continues (Film Ballad) - RaagTune.mp3 -> unknown - unknown - unknown.mp3
```

Apply changes (write metadata + move files to `music/op` or `music/nc`):

```bash
python music_organizer.py --apply
```

Run a second pass for unresolved files from `music/nc`:

```bash
python music_organizer.py --source-nc --metadata-json "metadata_patch.json" --apply
```

Validate a generated report:

```bash
python music_organizer.py --validate-report "music/music_organizer_report.json"
```

Or run helper script (double-click friendly):

```bash
python validate_report.py
```

Directory structure:

```text
music/
  ip/  # input
  op/  # output (changed)
  nc/  # no-change or missing metadata follow-up
```

## GUI

Run GUI mode:

```bash
python music_organizer.py
```

GUI includes:

- Folder browse and scan
- Search/filter over filenames and metadata
- Editable metadata fields per selected file
- Apply clean rules, save metadata, rename selected, process all
- Dry-run and metadata-write toggles

## Prompt Specs

Dedicated prompt/spec files are included:

- `planning.prompt.md`
- `implementation.prompt.md`

## Install

```bash
pip install -r requirements.txt
```

## Configuration

The Music Organizer uses an external `config.json` file to manage all customizable settings. This allows non-technical users to adjust behavior without editing Python code.

### config.json Location

Place `config.json` in the same directory as `music_organizer.py`. The script loads it automatically at startup. If the file is missing, built-in defaults are used.

### Configuration Sections

#### Application Settings

Controls default behavior for pattern, dry-run, and metadata writing:

```json
{
  "application": {
    "default_pattern": "{album} - {title}",
    "default_dry_run": true,
    "write_metadata_default": true,
    "description": "Application-level defaults"
  }
}
```

- `default_pattern`: Naming template used for file renaming (CLI and GUI)
- `default_dry_run`: If true, GUI defaults to preview mode (no file changes)
- `write_metadata_default`: If true, GUI defaults to writing metadata tags

#### Directory Settings

Configure where input/output/unresolved files are organized:

```json
{
  "directories": {
    "music_root": "music",
    "input": "ip",
    "output": "op",
    "nochange": "nc",
    "description": "Directory structure relative to music_root (music/ip, music/op, music/nc)"
  }
}
```

- `music_root`: Root folder for the workflow (default: "music")
- `input`, `output`, `nochange`: Subfolder names (combine with music_root: `music/ip`, `music/op`, `music/nc`)

#### Audio Settings

Control audio formats and metadata cleaning:

```json
{
  "audio": {
    "supported_extensions": [
      ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma"
    ],
    "noise_words": [
      "pagalnew", "raagtune", "320 kbps", "290 kbps", "128 kbps",
      "official", "lyrics", "Ghantalele.com", "(", ")"
    ],
    "description": "Audio format and metadata cleaning settings"
  }
}
```

- `supported_extensions`: List of file extensions to process (case-sensitive)
- `noise_words`: Phrases to remove from metadata during cleaning

#### Metadata Settings

Define editable fields and parsing rules:

```json
{
  "metadata": {
    "keys": ["artist", "title", "album", "track", "genre", "year", "original"],
    "editable_keys": ["artist", "title", "album", "track", "genre", "year"],
    "year_pattern_regex": "(?:\\(|\\[)?\\b(?:19|20)\\d{2}\\b(?:\\)|\\])?",
    "description": "Metadata field configuration"
  }
}
```

- `keys`: All metadata fields tracked (display-only list)
- `editable_keys`: Fields editable in the GUI metadata editor
- `year_pattern_regex`: Regex to detect and remove years from album names

### Example: Customizing Noise Words

To add a custom phrase to remove during cleaning, edit `config.json`:

```json
{
  "audio": {
    "noise_words": [
      "pagalnew",
      "raagtune",
      "my custom phrase",
      "another phrase to remove"
    ]
  }
}
```

### Example: Changing Default Naming Pattern

Edit the `default_pattern` in application settings:

```json
{
  "application": {
    "default_pattern": "{track} - {title} ({album})"
  }
}
```

Available placeholders: `{artist}`, `{title}`, `{album}`, `{track}`, `{genre}`, `{year}`, `{original}`

### Fallback Behavior

If `config.json` is missing or contains errors, the script uses built-in defaults:

- **Extensions**: MP3, FLAC, M4A, AAC, OGG, OPUS, WAV, WMA
- **Noise words**: pagalnew, raagtune, 320/290/128 kbps, official, lyrics, etc.
- **Pattern**: `{album} - {title}`
- **Dry-run**: True (preview mode by default)
- **Metadata writing**: True
- **Directories**: `music/ip`, `music/op`, `music/nc`

Errors during config load are printed to stderr but do not stop the program.

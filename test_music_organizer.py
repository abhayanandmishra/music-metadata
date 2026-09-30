import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import importlib.util


MODULE_PATH = Path(__file__).with_name("music_organizer.py")
spec = importlib.util.spec_from_file_location("music_organizer", MODULE_PATH)
rm = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(rm)
rm.load_config()


class RenameMusicTests(unittest.TestCase):
    def test_first_non_empty(self):
        self.assertEqual(rm.first_non_empty("", None, "value", "x"), "value")
        self.assertEqual(rm.first_non_empty("", " ", None), "")

    def test_get_easy_tag_with_alias(self):
        tags = {
            "comment": ["source comment"],
            "organization": ["Publisher Name"],
        }
        self.assertEqual(rm.get_easy_tag(tags, "comments", "comment", "description"), "source comment")
        self.assertEqual(rm.get_easy_tag(tags, "publisher", "organization", "label"), "Publisher Name")

    def test_set_easy_tag_with_alias_sets_value(self):
        tags = {}
        touched = rm.set_easy_tag(tags, "Publisher Name", "publisher", "organization")
        self.assertTrue(touched)
        self.assertEqual(tags.get("publisher") or tags.get("organization"), ["Publisher Name"])

    def test_validate_report_success(self):
        summary = {
            "createdAt": "2026-08-18T12:00:00",
            "folder": "music/ip",
            "dryRun": True,
            "writeMetadata": True,
            "pattern": "{album} - {title}",
            "files": [
                {
                    "file": "music/ip/a.mp3",
                    "originalName": "a.mp3",
                    "originalMetadata": {},
                    "cleanedMetadata": {},
                    "metadataUpdated": False,
                    "renamed": False,
                    "newName": "a.mp3",
                    "errors": [],
                    "status": "nc",
                }
            ],
            "errors": [],
            "totals": {
                "processed": 1,
                "metadataUpdated": 0,
                "renamed": 0,
                "op": 0,
                "nc": 1,
                "errors": 0,
            },
        }
        rm.validate_report(summary)

    def test_validate_report_failure_on_count_mismatch(self):
        summary = {
            "createdAt": "2026-08-18T12:00:00",
            "folder": "music/ip",
            "dryRun": True,
            "writeMetadata": True,
            "pattern": "{album} - {title}",
            "files": [],
            "errors": [],
            "totals": {
                "processed": 5,
                "metadataUpdated": 0,
                "renamed": 0,
                "op": 0,
                "nc": 0,
                "errors": 0,
            },
        }

        with self.assertRaises(ValueError) as ctx:
            rm.validate_report(summary)
        self.assertIn("processed", str(ctx.exception))

    def test_apply_external_metadata_only_fills_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "song.mp3"
            p.write_bytes(b"x")
            metadata = {
                "artist": "",
                "title": "Known Title",
                "album": "",
                "track": "",
                "genre": "",
                "year": "",
                "original": "song",
            }
            overrides = {
                "song.mp3": {
                    "artist": "New Artist",
                    "title": "Should Not Override",
                    "album": "New Album",
                }
            }

            out = rm.apply_external_metadata(p, metadata, overrides)
            self.assertEqual(out["artist"], "New Artist")
            self.assertEqual(out["album"], "New Album")
            self.assertEqual(out["title"], "Known Title")

    def test_ensure_music_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "music"
            ip, op, nc = rm.ensure_music_dirs(root)
            self.assertTrue(ip.exists() and ip.is_dir())
            self.assertTrue(op.exists() and op.is_dir())
            self.assertTrue(nc.exists() and nc.is_dir())

    def test_write_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            payload = {
                "createdAt": "2026-08-18T12:00:00",
                "folder": "music/ip",
                "dryRun": True,
                "writeMetadata": True,
                "pattern": "{album} - {title}",
                "files": [],
                "errors": [],
                "totals": {
                    "processed": 0,
                    "metadataUpdated": 0,
                    "renamed": 0,
                    "op": 0,
                    "nc": 0,
                    "errors": 0,
                },
            }
            rm.write_report(report, payload)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(data["totals"]["processed"], 0)

    def test_clean_noise_words_removes_tokens_from_title(self):
        title = "My Song - Downloaded from (Ghantalele.com) [official]"
        cleaned = rm.clean_noise_words(title)
        self.assertEqual(cleaned, "My Song")

    def test_clean_noise_words_removes_bare_ghantalele(self):
        title = "Andaz - Zindagi Ek Safar Hai Suhana Male Vocals Ghantalele"
        cleaned = rm.clean_noise_words(title)
        self.assertEqual(cleaned, "Andaz - Zindagi Ek Safar Hai Suhana Male Vocals")

    def test_clean_metadata_cleans_extended_fields(self):
        metadata = {
            "artist": "Artist",
            "title": "Title",
            "album": "Album",
            "track": "01",
            "genre": "Genre",
            "year": "2024",
            "original": "orig",
            "comments": "Downloaded from Ghantalele.com",
            "albumartist": "Album Artist (official)",
            "publisher": "Publisher Ghantalele.com",
            "composer": "Composer (Ghantalele.com)",
        }
        cleaned = rm.clean_metadata(metadata)
        self.assertEqual(cleaned["comments"], "")
        self.assertEqual(cleaned["albumartist"], "Album Artist")
        self.assertEqual(cleaned["publisher"], "Publisher")
        self.assertEqual(cleaned["composer"], "Composer")

    def test_metadata_changed_detects_extended_fields(self):
        left = {
            "artist": "A",
            "title": "T",
            "album": "AL",
            "track": "1",
            "genre": "G",
            "year": "2020",
            "comments": "x",
            "albumartist": "aa",
            "publisher": "pub",
            "composer": "comp",
        }
        right = dict(left)
        right["comments"] = ""
        self.assertTrue(rm.metadata_changed(left, right))

    def test_has_missing_core(self):
        self.assertTrue(rm.has_missing_core({"album": "", "title": "Title"}))
        self.assertTrue(rm.has_missing_core({"album": "Album", "title": ""}))
        self.assertFalse(rm.has_missing_core({"album": "Album", "title": "Title"}))

    def test_validate_report_missing_required_key(self):
        summary = {
            "createdAt": "2026-08-18T12:00:00",
            "folder": "music/ip",
            "dryRun": True,
            "writeMetadata": True,
            "pattern": "{album} - {title}",
            "files": [],
            # "errors" key intentionally missing
            "totals": {
                "processed": 0,
                "metadataUpdated": 0,
                "renamed": 0,
                "op": 0,
                "nc": 0,
                "errors": 0,
            },
        }
        with self.assertRaises(ValueError) as ctx:
            rm.validate_report(summary)
        self.assertIn("missing top-level keys", str(ctx.exception))

    def test_rename_files_moves_complete_unchanged_to_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "input"
            src.mkdir()
            path = src / "Album - Title.mp3"
            path.write_bytes(b"x")

            op = root / "op"
            nc = root / "nc"
            op.mkdir()
            nc.mkdir()

            original = {
                "artist": "Artist",
                "title": "Title",
                "album": "Album",
                "track": "1",
                "genre": "Genre",
                "year": "2024",
                "original": "Album - Title",
                "comments": "",
                "albumartist": "",
                "publisher": "",
                "composer": "",
            }
            completed = dict(original)

            with mock.patch.object(rm, "process_file", return_value=(original, completed)):
                processed = rm.rename_files(
                    src,
                    "{album} - {title}",
                    dry_run=False,
                    write_back=False,
                    apply_changes=True,
                    op_dir=op,
                    nc_dir=nc,
                )

            self.assertEqual(processed, 1)
            self.assertTrue((op / "Album - Title.mp3").exists())
            self.assertFalse(any(nc.iterdir()))

    def test_rename_files_moves_unresolved_to_nc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "input"
            src.mkdir()
            path = src / "track01.mp3"
            path.write_bytes(b"x")

            op = root / "op"
            nc = root / "nc"
            op.mkdir()
            nc.mkdir()

            original = {
                "artist": "",
                "title": "",
                "album": "",
                "track": "",
                "genre": "",
                "year": "",
                "original": "track01",
                "comments": "",
                "albumartist": "",
                "publisher": "",
                "composer": "",
            }
            completed = dict(original)

            with mock.patch.object(rm, "process_file", return_value=(original, completed)):
                processed = rm.rename_files(
                    src,
                    "{album} - {title}",
                    dry_run=False,
                    write_back=False,
                    apply_changes=True,
                    op_dir=op,
                    nc_dir=nc,
                )

            self.assertEqual(processed, 1)
            self.assertFalse(any(op.iterdir()))
            self.assertEqual(len(list(nc.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()

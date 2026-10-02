import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import music_organizer
from music_organizer import config
from music_organizer.core import metadata as rm
from music_organizer.analysis import audio_quality as aq

# Load config for global variables
config.load_config()


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


class AudioQualityAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = aq.AudioQualityAnalyzer()
        self.analyzer.ffmpeg_available = True

    def test_extract_ffmpeg_metric_prefers_last_match(self):
        text = """
        Overall RMS level dB: -18.2
        RMS level dB: -20.0
        """
        value = self.analyzer._extract_ffmpeg_metric(text, [r"Overall RMS level dB:\s*(-?\d+(?:\.\d+)?)", r"RMS level dB:\s*(-?\d+(?:\.\d+)?)"])
        self.assertEqual(value, "-18.2")

    def test_extract_metrics_uses_format_fallbacks(self):
        probe_json = json.dumps(
            {
                "streams": [
                    {
                        "codec_name": "mp3",
                        "bit_rate": None,
                        "sample_rate": "44100",
                        "channels": "2",
                        "duration": None,
                    }
                ],
                "format": {
                    "bit_rate": "192000",
                    "duration": "123.45",
                },
            }
        )

        def fake_run(cmd, capture_output=False, text=False, timeout=None, stdout=None, stderr=None):
            if cmd[0] == "ffprobe":
                return mock.Mock(returncode=0, stdout=probe_json, stderr="")
            if cmd[0] == "ffmpeg":
                stderr_text = """
                Overall RMS level dB: -18.0
                Overall peak level dB: -1.5
                Overall crest factor: 8.0
                Overall number of clipped samples: 10
                Overall number of samples: 1000
                """
                return mock.Mock(returncode=0, stdout="", stderr=stderr_text)
            raise AssertionError(f"Unexpected command: {cmd}")

        with mock.patch.object(aq.subprocess, "run", side_effect=fake_run):
            metrics = self.analyzer._extract_metrics(Path("sample.mp3"))

        self.assertEqual(metrics["bitrate"], 192)
        self.assertEqual(metrics["sample_rate"], 44100)
        self.assertEqual(metrics["channels"], 2)
        self.assertEqual(metrics["duration"], 123.45)
        self.assertEqual(metrics["loudness_mean"], -18.0)
        self.assertEqual(metrics["loudness_peak"], -1.5)
        self.assertEqual(metrics["clipping_ratio"], 0.01)
        self.assertIsNotNone(metrics["sound_score"])

    def test_analyze_returns_quality_score_and_tier(self):
        with mock.patch.object(self.analyzer, "_extract_metrics", return_value={
            "bitrate": 320,
            "sample_rate": 48000,
            "channels": 2,
            "codec": "flac",
            "duration": 180.0,
            "is_lossless": True,
            "loudness_mean": -14.0,
            "loudness_peak": -1.0,
            "clipping_ratio": 0.0,
            "dynamic_range": 10.0,
            "bass_level": -18.0,
            "treble_level": -20.0,
            "bass_score": 10.0,
            "treble_score": 10.0,
            "sound_score": 10.0,
            "error": None,
        }):
            result = self.analyzer.analyze(Path("sample.flac"))

        self.assertTrue(result["success"])
        self.assertEqual(result["quality_score"], 9.5)
        self.assertEqual(result["quality_tier"], "excellent")
        self.assertTrue(result["is_lossless"])

    def test_format_metrics_includes_audio_properties(self):
        text = self.analyzer.format_metrics(
            {
                "success": True,
                "quality_score": 7.5,
                "quality_tier": "good",
                "codec": "mp3",
                "is_lossless": False,
                "bitrate": 192,
                "sample_rate": 44100,
                "channels": 2,
                "duration": 123.0,
                "loudness_mean": -16.0,
                "loudness_peak": -2.0,
                "dynamic_range": 8.0,
                "clipping_ratio": 0.0,
                "bass_score": 6.0,
                "treble_score": 7.0,
                "sound_score": 8.0,
            }
        )
        self.assertIn("Quality Score: 7.5/10", text)
        self.assertIn("Loudness (RMS): -16.0 dB", text)
        self.assertIn("Bass Score: 6.0/10", text)
        self.assertIn("Sound Score: 8.0/10", text)


if __name__ == "__main__":
    unittest.main()

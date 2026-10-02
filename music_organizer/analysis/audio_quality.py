#!/usr/bin/env python3
"""
Audio Quality Analyzer Module

Analyzes audio files using ffmpeg to extract metadata and calculate quality scores.
Provides comprehensive audio metrics including bitrate, sample rate, channels, codec, and duration.
Calculates a 1-10 quality score based on:
- Bitrate (higher is better)
- Sample rate (optimal range 44.1kHz - 48kHz)
- Channels (stereo > mono)
- Codec quality and loss
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional


class AudioQualityAnalyzer:
    """Analyzes audio file properties and generates quality score."""
    
    # Quality scoring thresholds
    BITRATE_EXCELLENT = 320  # kbps
    BITRATE_GOOD = 192       # kbps
    BITRATE_FAIR = 128       # kbps
    BITRATE_POOR = 64        # kbps
    
    SAMPLE_RATE_PREFERRED = (44100, 48000)  # Hz
    SAMPLE_RATE_GOOD = (22050, 32000)       # Hz
    
    CODECS_LOSSLESS = {"flac", "alac", "ape", "wv"}
    CODECS_LOSSY_HIGH = {"aac", "opus"}
    CODECS_LOSSY_STANDARD = {"mp3", "ogg"}
    CODECS_LOSSY_POOR = {"m4a"}
    
    TARGET_LOUDNESS = -14.0
    MAX_CLIPPING_RATIO = 0.01
    MIN_DYNAMIC_RANGE = 6.0
    
    def __init__(self):
        """Initialize analyzer. Check for ffmpeg availability."""
        self.ffmpeg_available = self._check_ffmpeg()
    
    @staticmethod
    def _check_ffmpeg() -> bool:
        """Check if ffmpeg is available in system PATH."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def analyze(self, path: Path) -> Dict:
        """
        Analyze audio file and return comprehensive metrics.
        
        Returns dict with:
            - success: bool (whether analysis succeeded)
            - bitrate: int (kbps) or None
            - sample_rate: int (Hz) or None
            - channels: int (1=mono, 2=stereo, etc.) or None
            - codec: str (e.g., "mp3", "flac") or None
            - duration: float (seconds) or None
            - is_lossless: bool
            - quality_score: float (1-10)
            - quality_tier: str ("poor", "fair", "good", "excellent")
            - error: str (if failed)
        """
        result = {
            "success": False,
            "bitrate": None,
            "sample_rate": None,
            "channels": None,
            "codec": None,
            "duration": None,
            "is_lossless": False,
            "loudness_mean": None,
            "loudness_peak": None,
            "clipping_ratio": None,
            "dynamic_range": None,
            "bass_level": None,
            "treble_level": None,
            "bass_score": None,
            "treble_score": None,
            "sound_score": None,
            "quality_score": 0,
            "quality_tier": "unknown",
            "error": None,
        }
        
        if not self.ffmpeg_available:
            result["error"] = "ffmpeg not available"
            return result
        
        if not path.exists():
            result["error"] = f"File not found: {path}"
            return result
        
        try:
            metrics = self._extract_metrics(path)
            if metrics["error"]:
                result["error"] = metrics["error"]
                return result
            
            result.update(metrics)
            result["success"] = True
            
            # Calculate quality score
            score = self._calculate_score(
                metrics["bitrate"],
                metrics["sample_rate"],
                metrics["channels"],
                metrics["codec"],
                metrics
            )
            result["quality_score"] = round(score, 1)
            result["quality_tier"] = self._score_to_tier(score)
            
        except Exception as e:
            result["error"] = f"Analysis failed: {str(e)}"
        
        return result
    
    def _extract_metrics(self, path: Path) -> Dict:
        """Extract audio metrics using ffprobe."""
        result = {
            "bitrate": None,
            "sample_rate": None,
            "channels": None,
            "codec": None,
            "duration": None,
            "is_lossless": False,
            "loudness_mean": None,
            "loudness_peak": None,
            "clipping_ratio": None,
            "dynamic_range": None,
            "bass_level": None,
            "treble_level": None,
            "bass_score": None,
            "treble_score": None,
            "sound_score": None,
            "error": None,
        }
        
        try:
            # Use ffprobe to extract audio stream information
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,bit_rate,sample_rate,channels,duration",
                "-of", "json",
                str(path)
            ]
            
            output = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if output.returncode != 0:
                result["error"] = f"ffprobe error: {output.stderr}"
                return result
            
            data = json.loads(output.stdout)
            streams = data.get("streams", [])
            format_info = data.get("format", {})
            
            if not streams:
                result["error"] = "No audio stream found"
                return result
            
            stream = streams[0]
            
            # Extract bitrate (convert to kbps)
            bitrate = self._coerce_int(stream.get("bit_rate"))
            if bitrate is None:
                bitrate = self._coerce_int(format_info.get("bit_rate"))
            if bitrate is not None:
                result["bitrate"] = bitrate // 1000
            
            # Extract sample rate
            sample_rate = self._coerce_int(stream.get("sample_rate"))
            if sample_rate is not None:
                result["sample_rate"] = sample_rate
            
            # Extract channels
            channels = self._coerce_int(stream.get("channels"))
            if channels is not None:
                result["channels"] = channels
            
            # Extract codec
            codec = stream.get("codec_name")
            if codec:
                result["codec"] = codec.lower()
                result["is_lossless"] = codec.lower() in self.CODECS_LOSSLESS
            
            # Extract duration
            duration = self._coerce_float(stream.get("duration"))
            if duration is None:
                duration = self._coerce_float(format_info.get("duration"))
            if duration is not None:
                result["duration"] = duration

            sound_metrics = self._extract_sound_metrics(path)
            result.update({k: v for k, v in sound_metrics.items() if v is not None})
            
        except json.JSONDecodeError as e:
            result["error"] = f"JSON decode error: {str(e)}"
        except subprocess.TimeoutExpired:
            result["error"] = "ffprobe timeout"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result

    def _extract_sound_metrics(self, path: Path) -> Dict:
        """Extract loudness, clipping, dynamic range, bass and treble estimates using ffmpeg."""
        result = {
            "loudness_mean": None,
            "loudness_peak": None,
            "clipping_ratio": None,
            "dynamic_range": None,
            "bass_level": None,
            "treble_level": None,
            "bass_score": None,
            "treble_score": None,
            "sound_score": None,
        }

        try:
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i", str(path),
                "-af", "astats=metadata=1:reset=1",
                "-f", "null", "-",
            ]
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            stderr = output.stderr or ""

            peak = self._extract_ffmpeg_metric(stderr, [
                r"Overall peak level dB:\s*(-?\d+(?:\.\d+)?)",
                r"Peak level dB:\s*(-?\d+(?:\.\d+)?)",
            ])
            rms = self._extract_ffmpeg_metric(stderr, [
                r"Overall RMS level dB:\s*(-?\d+(?:\.\d+)?)",
                r"RMS level dB:\s*(-?\d+(?:\.\d+)?)",
                r"Mean volume dB:\s*(-?\d+(?:\.\d+)?)",
            ])
            crest = self._extract_ffmpeg_metric(stderr, [
                r"Overall crest factor:\s*(-?\d+(?:\.\d+)?)",
                r"Crest factor:\s*(-?\d+(?:\.\d+)?)",
            ])
            clipped = self._coerce_float(self._extract_ffmpeg_metric(stderr, [
                r"Overall number of clipped samples:\s*(\d+(?:\.\d+)?)",
                r"Number of clipped samples:\s*(\d+(?:\.\d+)?)",
            ]))
            samples = self._coerce_float(self._extract_ffmpeg_metric(stderr, [
                r"Overall number of samples:\s*(\d+(?:\.\d+)?)",
                r"Number of samples:\s*(\d+(?:\.\d+)?)",
            ]))

            result["loudness_peak"] = peak
            result["loudness_mean"] = rms
            result["dynamic_range"] = max(0.0, crest) if crest is not None else None

            if clipped is not None and samples and samples > 0:
                result["clipping_ratio"] = min(1.0, clipped / samples)

            bass_level = self._probe_band_rms(path, "lowpass=f=180,astats=metadata=1:reset=1")
            treble_level = self._probe_band_rms(path, "highpass=f=5000,astats=metadata=1:reset=1")
            result["bass_level"] = bass_level
            result["treble_level"] = treble_level
            result["bass_score"] = self._score_band_level(bass_level, target=-18.0)
            result["treble_score"] = self._score_band_level(treble_level, target=-20.0)
            result["sound_score"] = self._calculate_sound_score(
                rms=rms,
                peak=peak,
                crest=crest,
                clipping_ratio=result["clipping_ratio"],
                bass_level=bass_level,
                treble_level=treble_level,
            )
        except Exception:
            # Sound metrics are optional. Keep analysis resilient.
            pass

        return result

    @staticmethod
    def _extract_ffmpeg_metric(text: str, patterns: list[str]) -> Optional[str]:
        """Return the last matching value for the first pattern that matches."""
        for pattern in patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if matches:
                return matches[-1]
        return None

    @staticmethod
    def _coerce_int(value) -> Optional[int]:
        try:
            if value is None:
                return None
            if isinstance(value, bool):
                return None
            return int(str(value).strip())
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _coerce_float(value) -> Optional[float]:
        try:
            if value is None:
                return None
            if isinstance(value, bool):
                return None
            return float(str(value).strip())
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _parse_ffmpeg_float(text: str, pattern: str) -> Optional[float]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            return None

    def _probe_band_rms(self, path: Path, filter_chain: str) -> Optional[float]:
        try:
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i", str(path),
                "-af", filter_chain,
                "-f", "null", "-",
            ]
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            return self._parse_ffmpeg_float(output.stderr or "", r"RMS level dB:\s*(-?\d+(?:\.\d+)?)")
        except Exception:
            return None

    @staticmethod
    def _score_band_level(band_rms: Optional[float], target: float) -> float:
        if band_rms is None:
            return 5.0
        distance = abs(band_rms - target)
        return max(1.0, min(10.0, 10.0 - min(9.0, distance / 3.0)))

    def _calculate_sound_score(
        self,
        rms: Optional[float],
        peak: Optional[float],
        crest: Optional[float],
        clipping_ratio: Optional[float],
        bass_level: Optional[float],
        treble_level: Optional[float],
    ) -> float:
        score = 5.0

        if rms is not None:
            score += max(-1.5, 2.0 - (abs(rms - self.TARGET_LOUDNESS) / 3.0))

        if peak is not None:
            if peak > -1.0:
                score -= 2.0
            elif peak > -3.0:
                score -= 0.5
            else:
                score += 0.5

        if crest is not None:
            if crest >= self.MIN_DYNAMIC_RANGE:
                score += min(1.5, crest / 10.0)
            else:
                score -= 1.0

        if clipping_ratio is not None:
            if clipping_ratio <= self.MAX_CLIPPING_RATIO:
                score += 1.0
            else:
                score -= min(2.0, clipping_ratio * 50.0)

        if bass_level is not None and treble_level is not None:
            balance = abs(bass_level - treble_level)
            if balance <= 4.0:
                score += 1.0
            elif balance <= 8.0:
                score += 0.25
            else:
                score -= 0.75

        return max(1.0, min(10.0, score))
    
    def _calculate_score(
        self,
        bitrate: Optional[int],
        sample_rate: Optional[int],
        channels: Optional[int],
        codec: Optional[str],
        metrics: Optional[Dict] = None
    ) -> float:
        """
        Calculate audio quality score (1-10).
        
        Scoring logic:
        - Lossless: Start at 10, deduct only for unusual sample rates
        - Lossy high quality (320+ kbps, 48kHz, stereo): 9-10
        - Lossy good quality (192+ kbps, 44.1kHz, stereo): 7-8
        - Lossy fair quality (128 kbps, 44.1kHz, stereo): 5-6
        - Lossy poor quality (64 kbps or mono): 2-4
        """
        
        if not codec:
            return 1.0  # Unknown codec
        
        codec_lower = codec.lower()
        
        # Lossless codecs get high score
        if codec_lower in self.CODECS_LOSSLESS:
            score = 9.5
            # Slight deduction for unusual sample rates
            if sample_rate and sample_rate not in self.SAMPLE_RATE_PREFERRED:
                score -= 0.5
            return min(10.0, score)
        
        # Lossy codec scoring
        score = 5.0  # Base score for lossy
        
        # Codec quality bonus
        if codec_lower in self.CODECS_LOSSY_HIGH:
            score += 2.0
        elif codec_lower in self.CODECS_LOSSY_STANDARD:
            score += 1.0
        elif codec_lower in self.CODECS_LOSSY_POOR:
            score -= 0.5
        
        # Bitrate scoring (most important for lossy)
        if bitrate:
            if bitrate >= self.BITRATE_EXCELLENT:
                score += 2.5
            elif bitrate >= self.BITRATE_GOOD:
                score += 1.5
            elif bitrate >= self.BITRATE_FAIR:
                score += 0.5
            elif bitrate >= self.BITRATE_POOR:
                score -= 1.0
            else:
                score -= 2.0
        else:
            score -= 1.0  # Unknown bitrate penalty
        
        # Sample rate scoring
        if sample_rate:
            if sample_rate in self.SAMPLE_RATE_PREFERRED:
                score += 0.5
            elif sample_rate in self.SAMPLE_RATE_GOOD:
                score += 0.0
            else:
                score -= 0.5
        
        # Channel scoring
        if channels:
            if channels >= 2:
                score += 0.5
            elif channels == 1:
                score -= 1.0  # Mono penalty
        else:
            score -= 0.5

        if metrics:
            sound_score = metrics.get("sound_score")
            if isinstance(sound_score, (int, float)):
                score = (score * 0.7) + (float(sound_score) * 0.3)

            bass_score = metrics.get("bass_score")
            treble_score = metrics.get("treble_score")
            if isinstance(bass_score, (int, float)) and isinstance(treble_score, (int, float)):
                score = (score * 0.85) + (((float(bass_score) + float(treble_score)) / 2.0) * 0.15)
        
        # Clamp score to 1-10 range
        return max(1.0, min(10.0, score))
    
    @staticmethod
    def _score_to_tier(score: float) -> str:
        """Convert numeric score to quality tier."""
        if score >= 9.0:
            return "excellent"
        elif score >= 7.0:
            return "good"
        elif score >= 5.0:
            return "fair"
        else:
            return "poor"
    
    def format_metrics(self, metrics: Dict) -> str:
        """Format metrics dict as human-readable string."""
        if not metrics.get("success"):
            return f"Analysis failed: {metrics.get('error', 'Unknown error')}"
        
        lines = [
            f"Quality Score: {metrics['quality_score']}/10 ({metrics['quality_tier'].upper()})",
            f"Codec: {metrics['codec'] or 'Unknown'} {'(Lossless)' if metrics['is_lossless'] else '(Lossy)'}",
            f"Bitrate: {metrics['bitrate']} kbps" if metrics['bitrate'] else "Bitrate: Unknown",
            f"Sample Rate: {metrics['sample_rate']} Hz" if metrics['sample_rate'] else "Sample Rate: Unknown",
            f"Channels: {metrics['channels']} {'(Mono)' if metrics['channels'] == 1 else '(Stereo)' if metrics['channels'] == 2 else f'(Ch)'}",
            f"Duration: {self._format_duration(metrics['duration'])}" if metrics['duration'] else "Duration: Unknown",
            f"Loudness (RMS): {metrics['loudness_mean']} dB" if metrics.get('loudness_mean') is not None else "Loudness (RMS): Unknown",
            f"Peak Level: {metrics['loudness_peak']} dB" if metrics.get('loudness_peak') is not None else "Peak Level: Unknown",
            f"Dynamic Range: {metrics['dynamic_range']}" if metrics.get('dynamic_range') is not None else "Dynamic Range: Unknown",
            f"Clipping Ratio: {round((metrics['clipping_ratio'] or 0) * 100, 3)}%" if metrics.get('clipping_ratio') is not None else "Clipping Ratio: Unknown",
            f"Bass Score: {metrics['bass_score']}/10" if metrics.get('bass_score') is not None else "Bass Score: Unknown",
            f"Treble Score: {metrics['treble_score']}/10" if metrics.get('treble_score') is not None else "Treble Score: Unknown",
            f"Sound Score: {metrics['sound_score']}/10" if metrics.get('sound_score') is not None else "Sound Score: Unknown",
        ]
        return "\n  ".join(lines)
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds as HH:MM:SS."""
        if not seconds:
            return "Unknown"
        total = int(seconds)
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"


def analyze_file(path: Path) -> Dict:
    """Convenience function to analyze a single file."""
    analyzer = AudioQualityAnalyzer()
    return analyzer.analyze(path)

"""
VeilCore Audio Alert System
==============================
Severity-mapped audio alert generation for
auditory situational awareness.

Tone profiles:
    CRITICAL — Rapid triple-pulse, high frequency (880Hz)
    HIGH     — Double-pulse, mid-high frequency (660Hz)
    MEDIUM   — Single pulse, mid frequency (440Hz)
    LOW      — Soft single, low frequency (330Hz)
    INFO     — Brief click, very low frequency (220Hz)

Generates tone specifications compatible with:
    - Linux ALSA / PulseAudio (via aplay or paplay)
    - Web Audio API (for dashboard)
    - Piezo buzzers (embedded systems)
    - Assistive device haptic feedback
"""

from __future__ import annotations

import json
import logging
import math
import os
import struct
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.accessibility.audio")


@dataclass
class ToneProfile:
    """Audio tone definition."""
    frequency_hz: float
    duration_ms: int
    pulses: int = 1
    pulse_gap_ms: int = 100
    volume: float = 0.8        # 0.0 - 1.0
    waveform: str = "sine"     # sine, square, triangle
    fade_ms: int = 20          # Fade in/out to prevent clicks

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequency_hz": self.frequency_hz,
            "duration_ms": self.duration_ms,
            "pulses": self.pulses,
            "pulse_gap_ms": self.pulse_gap_ms,
            "volume": self.volume,
            "waveform": self.waveform,
            "fade_ms": self.fade_ms,
        }

    @property
    def total_duration_ms(self) -> int:
        return (self.duration_ms * self.pulses) + (self.pulse_gap_ms * (self.pulses - 1))


# Severity-mapped tone profiles
SEVERITY_TONES = {
    "critical": ToneProfile(
        frequency_hz=880.0, duration_ms=150, pulses=3,
        pulse_gap_ms=80, volume=0.9, waveform="square",
    ),
    "high": ToneProfile(
        frequency_hz=660.0, duration_ms=200, pulses=2,
        pulse_gap_ms=120, volume=0.8, waveform="sine",
    ),
    "medium": ToneProfile(
        frequency_hz=440.0, duration_ms=250, pulses=1,
        volume=0.6, waveform="sine",
    ),
    "low": ToneProfile(
        frequency_hz=330.0, duration_ms=300, pulses=1,
        volume=0.4, waveform="sine",
    ),
    "info": ToneProfile(
        frequency_hz=220.0, duration_ms=100, pulses=1,
        volume=0.3, waveform="triangle",
    ),
}

# Special event tones
EVENT_TONES = {
    "organ_failure": ToneProfile(
        frequency_hz=520.0, duration_ms=400, pulses=2,
        pulse_gap_ms=200, volume=0.85, waveform="square",
    ),
    "kill_switch": ToneProfile(
        frequency_hz=1000.0, duration_ms=100, pulses=5,
        pulse_gap_ms=50, volume=1.0, waveform="square",
    ),
    "all_clear": ToneProfile(
        frequency_hz=523.25, duration_ms=300, pulses=2,
        pulse_gap_ms=100, volume=0.5, waveform="sine",
    ),
    "federation_sync": ToneProfile(
        frequency_hz=392.0, duration_ms=200, pulses=1,
        volume=0.3, waveform="triangle",
    ),
    "scan_complete": ToneProfile(
        frequency_hz=587.33, duration_ms=150, pulses=2,
        pulse_gap_ms=80, volume=0.4, waveform="sine",
    ),
}


class AudioAlertSystem:
    """
    Generates audio alerts for VeilCore events.

    Usage:
        audio = AudioAlertSystem()
        wav_data = audio.generate_wav("critical")
        audio.save_wav("critical", "/tmp/alert.wav")
        spec = audio.get_web_audio_spec("high")
    """

    SAMPLE_RATE = 44100

    def __init__(self, output_dir: str = "/var/lib/veilcore/accessibility"):
        self._output_dir = output_dir
        self._all_tones = {**SEVERITY_TONES, **EVENT_TONES}

    def get_tone(self, name: str) -> Optional[ToneProfile]:
        """Get tone profile by name."""
        return self._all_tones.get(name)

    def generate_samples(self, tone: ToneProfile) -> list[int]:
        """Generate raw PCM samples for a tone."""
        samples = []
        samples_per_ms = self.SAMPLE_RATE / 1000

        for pulse in range(tone.pulses):
            pulse_samples = int(tone.duration_ms * samples_per_ms)
            fade_samples = int(tone.fade_ms * samples_per_ms)

            for i in range(pulse_samples):
                t = i / self.SAMPLE_RATE

                # Generate waveform
                if tone.waveform == "sine":
                    value = math.sin(2 * math.pi * tone.frequency_hz * t)
                elif tone.waveform == "square":
                    value = 1.0 if math.sin(2 * math.pi * tone.frequency_hz * t) >= 0 else -1.0
                elif tone.waveform == "triangle":
                    period = 1.0 / tone.frequency_hz
                    phase = (t % period) / period
                    value = 4.0 * abs(phase - 0.5) - 1.0
                else:
                    value = math.sin(2 * math.pi * tone.frequency_hz * t)

                # Apply volume
                value *= tone.volume

                # Apply fade in/out
                if i < fade_samples:
                    value *= i / fade_samples
                elif i > pulse_samples - fade_samples:
                    value *= (pulse_samples - i) / fade_samples

                # Convert to 16-bit integer
                sample = max(-32767, min(32767, int(value * 32767)))
                samples.append(sample)

            # Add gap between pulses
            if pulse < tone.pulses - 1:
                gap_samples = int(tone.pulse_gap_ms * samples_per_ms)
                samples.extend([0] * gap_samples)

        return samples

    def generate_wav(self, tone_name: str) -> Optional[bytes]:
        """Generate WAV file bytes for a tone."""
        tone = self._all_tones.get(tone_name)
        if not tone:
            return None

        samples = self.generate_samples(tone)
        return self._encode_wav(samples)

    def save_wav(self, tone_name: str, path: str) -> bool:
        """Save tone as WAV file."""
        wav_data = self.generate_wav(tone_name)
        if not wav_data:
            return False
        try:
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            with open(path, "wb") as f:
                f.write(wav_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save WAV: {e}")
            return False

    def generate_all_wavs(self, output_dir: Optional[str] = None) -> dict[str, str]:
        """Generate WAV files for all tones."""
        out = output_dir or self._output_dir
        os.makedirs(out, exist_ok=True)
        paths = {}
        for name in self._all_tones:
            path = os.path.join(out, f"alert_{name}.wav")
            if self.save_wav(name, path):
                paths[name] = path
        return paths

    def get_web_audio_spec(self, tone_name: str) -> Optional[dict[str, Any]]:
        """
        Get Web Audio API specification for a tone.
        Can be used by the dashboard's JavaScript to play alerts.
        """
        tone = self._all_tones.get(tone_name)
        if not tone:
            return None
        return {
            "type": tone.waveform if tone.waveform != "triangle" else "triangle",
            "frequency": tone.frequency_hz,
            "duration": tone.duration_ms / 1000,
            "pulses": tone.pulses,
            "pulseGap": tone.pulse_gap_ms / 1000,
            "volume": tone.volume,
            "fadeIn": tone.fade_ms / 1000,
            "fadeOut": tone.fade_ms / 1000,
        }

    def get_all_web_audio_specs(self) -> dict[str, dict[str, Any]]:
        """Get Web Audio specs for all tones."""
        return {
            name: self.get_web_audio_spec(name)
            for name in self._all_tones
            if self.get_web_audio_spec(name) is not None
        }

    def list_tones(self) -> list[dict[str, Any]]:
        """List all available tones."""
        return [
            {"name": name, **tone.to_dict()}
            for name, tone in self._all_tones.items()
        ]

    def _encode_wav(self, samples: list[int]) -> bytes:
        """Encode samples as WAV file bytes."""
        import io
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.SAMPLE_RATE)
            data = struct.pack(f"<{len(samples)}h", *samples)
            w.writeframes(data)
        return buf.getvalue()

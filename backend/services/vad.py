from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SegmentResult:
    audio: np.ndarray
    duration_seconds: float
    energy: float


@dataclass(slots=True)
class VoiceActivityDetector:
    sample_rate: int
    energy_threshold: float
    silence_timeout_seconds: float
    minimum_speech_seconds: float
    maximum_segment_seconds: float
    _active_chunks: List[np.ndarray] = field(default_factory=list)
    _speech_started: bool = False
    _speech_duration: float = 0.0
    _silence_duration: float = 0.0
    _peak_energy: float = 0.0

    def process_chunk(self, chunk: np.ndarray) -> SegmentResult | None:
        if chunk.size == 0:
            return None

        mono_chunk = chunk.reshape(-1)
        duration = len(mono_chunk) / self.sample_rate
        energy = float(np.sqrt(np.mean(np.square(mono_chunk))) + 1e-12)
        self._peak_energy = max(self._peak_energy, energy)

        is_speech = energy >= self.energy_threshold
        if is_speech:
            if not self._speech_started:
                logger.info('Speech started (energy=%.5f, threshold=%.5f)', energy, self.energy_threshold)
            self._speech_started = True
            self._silence_duration = 0.0
            self._speech_duration += duration
            self._active_chunks.append(mono_chunk.copy())
        elif self._speech_started:
            self._silence_duration += duration
            self._active_chunks.append(mono_chunk.copy())
            if self._silence_duration >= self.silence_timeout_seconds:
                return self._finish_segment()

        if self._speech_started and self._speech_duration >= self.maximum_segment_seconds:
            logger.info('Speech segment reached max duration %.2fs; forcing flush', self.maximum_segment_seconds)
            return self._finish_segment()

        return None

    def _finish_segment(self) -> SegmentResult | None:
        if not self._active_chunks:
            self._reset()
            return None

        audio = np.concatenate(self._active_chunks)
        duration_seconds = len(audio) / self.sample_rate
        mean_energy = float(np.sqrt(np.mean(np.square(audio))) + 1e-12)

        if self._speech_duration < self.minimum_speech_seconds:
            logger.info(
                'Segment ignored (speech %.2fs < minimum %.2fs, peak energy %.5f)',
                self._speech_duration,
                self.minimum_speech_seconds,
                self._peak_energy,
            )
            self._reset()
            return None

        logger.info(
            'Speech ended (duration %.2fs, silence %.2fs, energy %.5f)',
            duration_seconds,
            self._silence_duration,
            mean_energy,
        )
        result = SegmentResult(audio=audio, duration_seconds=duration_seconds, energy=mean_energy)
        self._reset()
        return result

    def flush(self) -> SegmentResult | None:
        if not self._speech_started:
            return None
        return self._finish_segment()

    def _reset(self) -> None:
        self._active_chunks.clear()
        self._speech_started = False
        self._speech_duration = 0.0
        self._silence_duration = 0.0
        self._peak_energy = 0.0


# TODO: Replace or augment this simple energy VAD with WebRTC VAD for noisier rooms.

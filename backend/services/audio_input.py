from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List

import numpy as np
import sounddevice as sd

from backend.config import Settings
from backend.models import DeviceInfo

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioChunk:
    data: np.ndarray


class AudioInputService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._stream: sd.InputStream | None = None
        self._queue: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=200)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._selected_device: DeviceInfo | None = None
        self._started = False

    def list_input_devices(self) -> List[DeviceInfo]:
        devices = sd.query_devices()
        items: List[DeviceInfo] = []
        for index, device in enumerate(devices):
            if device['max_input_channels'] <= 0:
                continue
            items.append(
                DeviceInfo(
                    index=index,
                    name=str(device['name']),
                    max_input_channels=int(device['max_input_channels']),
                    default_samplerate=float(device['default_samplerate']),
                )
            )
        return items

    def get_selected_device(self) -> DeviceInfo | None:
        return self._selected_device

    async def start(self) -> None:
        if self._started or self.settings.test_mode:
            if self.settings.test_mode:
                logger.info('Audio input disabled because TEST_MODE=true')
            return

        self._loop = asyncio.get_running_loop()
        device = self._resolve_device()
        self._selected_device = device

        logger.info(
            'Using audio device index=%s name=%s sample_rate=%s channels=%s',
            device.index,
            device.name,
            self.settings.sample_rate,
            self.settings.channels,
        )

        def callback(indata, frames, time_info, status) -> None:  # type: ignore[no-untyped-def]
            del frames, time_info
            if status:
                logger.warning('Audio callback status: %s', status)
            chunk = np.copy(indata[:, 0]).astype(np.float32)
            if self._loop is None:
                return
            self._loop.call_soon_threadsafe(self._push_chunk, chunk)

        self._stream = sd.InputStream(
            device=device.index,
            samplerate=self.settings.sample_rate,
            channels=self.settings.channels,
            dtype=self.settings.dtype,
            blocksize=self.settings.block_size,
            callback=callback,
        )
        self._stream.start()
        self._started = True

    def _push_chunk(self, chunk: np.ndarray) -> None:
        try:
            self._queue.put_nowait(AudioChunk(data=chunk))
        except asyncio.QueueFull:
            logger.warning('Audio queue full; dropping chunk to preserve real-time flow')

    async def read_chunk(self) -> AudioChunk:
        return await self._queue.get()

    async def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._started = False

    def _resolve_device(self) -> DeviceInfo:
        devices = self.list_input_devices()
        if not devices:
            raise RuntimeError('No input audio devices were found.')

        if self.settings.device_index is not None:
            for device in devices:
                if device.index == self.settings.device_index:
                    return device
            raise RuntimeError(f'Configured AUDIO_DEVICE_INDEX={self.settings.device_index} was not found.')

        if self.settings.device_name:
            needle = self.settings.device_name.lower()
            for device in devices:
                if needle in device.name.lower():
                    return device
            raise RuntimeError(f'Configured AUDIO_DEVICE_NAME={self.settings.device_name!r} was not found.')

        default_input = sd.default.device[0]
        for device in devices:
            if device.index == default_input:
                return device
        return devices[0]

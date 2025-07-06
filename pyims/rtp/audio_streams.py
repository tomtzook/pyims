import threading
import time
import wave
from pathlib import Path
from typing import Optional, Callable

from pyims.nio.streams import ReadableStream, WritableStream


class WaveFileReadableStream(ReadableStream[bytes]):

    def __init__(self, path: Path,  rate: int, sample_width: int):
        self._path = path
        self._rate = rate
        self._sample_width = sample_width
        self._read_thread = None
        self._stop_event = threading.Event()

    def start_read(self, callback: Callable[[Optional[bytes]], None]):
        if self._read_thread is not None:
            raise RuntimeError('already running')

        self._stop_event.clear()
        self._read_thread = threading.Thread(target=self._read_main, args=(callback,), daemon=True)
        self._read_thread.start()

    def __del__(self):
        if self._read_thread is not None:
            self._stop_event.set()
            self._read_thread.join()

    def _read_main(self, callback: Callable[[Optional[bytes]], None]):
        with wave.open(str(self._path), 'rb') as f:
            while True:
                start = time.monotonic_ns()

                payload = f.readframes(80 * self._sample_width)
                if payload is None or len(payload) < 1:
                    callback(None)
                    break

                callback(payload)

                delay = (1 / self._rate) * 160
                proc_time = (time.monotonic_ns() - start) / 1e9
                sleep_time = delay - proc_time
                sleep_time = max(0, sleep_time)

                if self._stop_event.wait(sleep_time):
                    break


class WaveFileWritableStream(WritableStream[bytes]):

    def __init__(self, path: Path, rate: int, channels: int, sample_width: int):
        self._path = path
        self._rate = rate
        self._channels = channels
        self._sample_width = sample_width
        self._fobj = None

    def write(self, data: bytes):
        if self._fobj is None:
            self._fobj = wave.open(str(self._path), 'wb')
            self._fobj.setframerate(self._rate)
            self._fobj.setnchannels(self._channels)
            self._fobj.setsampwidth(self._sample_width)

        self._fobj.writeframes(data)

    def write_done(self):
        if self._fobj is not None:
            self._fobj.close()
            self._fobj = None

    def __del__(self):
        if self._fobj is not None:
            self._fobj.close()
            self._fobj = None

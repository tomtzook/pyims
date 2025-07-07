import io
from collections import deque
from typing import Optional, Callable

from ..nio import create_udp_socket
from .call import CallSession, CallInfo
from ..nio.streams import ReadableStream, WritableStream
from ..rtp.codecs import get_encoder, get_decoder
from ..rtp.stream import RtpStream


class CallOutStream(ReadableStream[bytes]):

    def __init__(self):
        self._is_reading = False
        self._callback = None
        self._streams = deque()
        self._current_stream = None
        self._current_stream_callback = None

    def start_read(self, callback: Callable[[Optional[bytes]], None]):
        self._is_reading = True
        self._callback = callback

        if len(self._streams) > 0:
            self._start_read_next()

    def attach_stream(self, stream: ReadableStream[bytes], on_finish: Optional[Callable[[], None]] = None):
        self._streams.append((stream, on_finish))

        if self._is_reading and self._current_stream is None:
            self._start_read_next()

    def _start_read_next(self):
        if self._current_stream is not None and self._current_stream_callback is not None:
            self._current_stream_callback()

        if len(self._streams) < 1:
            # we are done
            self._current_stream = None
            self._callback(None)
            return

        stream, callback = self._streams.popleft()
        stream.start_read(self._on_read)
        self._current_stream = stream
        self._current_stream_callback = callback

    def _on_read(self, data: Optional[bytes]):
        if data is None:
            self._start_read_next()
        else:
            self._callback(data)


class CallInStream(WritableStream[bytes]):

    def __init__(self):
        self._buffer = io.BytesIO()
        self._stream = None

    def write(self, data: bytes):
        if self._stream is not None:
            self._stream.write(data)
        else:
            self._buffer.write(data)

    def write_done(self):
        if self._stream is not None:
            self._stream.write_done()

    def attach(self, stream: WritableStream[bytes]):
        self._stream = stream

        data = self._buffer.read()
        if data is not None:
            self._stream.write(data)


class RtpCallSession(CallSession):

    def __init__(self, info: CallInfo):
        super().__init__(info)
        self._call_in = CallInStream()
        self._call_out = CallOutStream()

        skt = create_udp_socket(bind_addr=info.local_address)
        self._stream = RtpStream(
            skt,
            self._call_out,
            self._call_in,
            info.remote_address,
            info.media_format,
            get_encoder(info.media_format),
            get_decoder(info.media_format),
            1
        )

    def start(self):
        self._stream.start()

    def terminate(self):
        self._stream.stop()

    def attach_out(self, stream: ReadableStream[bytes], on_finish: Optional[Callable[[], None]] = None):
        self._call_out.attach_stream(stream, on_finish)

    def attach_in(self, stream: WritableStream[bytes]):
        self._call_in.attach(stream)

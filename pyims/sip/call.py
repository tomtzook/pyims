import enum
import io
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from typing import Callable, Optional

from ..nio.inet import InetAddress
from ..nio.streams import ReadableStream, WritableStream
from ..rtp.audio_streams import WaveFileWritableStream, WaveFileReadableStream
from ..sdp.message import SdpMessage
from ..sdp.fields import ConnectionInformation, MediaDescription
from ..sdp.attributes import RtpMap
from ..rtp.codecs import get_encoder, get_decoder
from ..rtp.stream import RtpStream
from ..nio.sockets import UdpSocket
from ..sdp.sdp_types import AddressType, MediaType, MediaProtocol, MediaFormat


class CallInformation(object):

    def __init__(self, local_info: SdpMessage, remote_info: SdpMessage):
        local_conn_info = local_info.field(ConnectionInformation)
        local_media_info = local_info.field(MediaDescription)
        remote_conn_info = remote_info.field(ConnectionInformation)
        remote_media_info = remote_info.field(MediaDescription)

        assert local_conn_info.address_type == remote_conn_info.address_type == AddressType.IPv4
        assert local_media_info.media_type == remote_media_info.media_type == MediaType.AUDIO
        assert local_media_info.protocol == remote_media_info.protocol == MediaProtocol.RTP_AVP
        assert len(local_media_info.formats) > 0 and len(remote_media_info.formats) > 0
        assert local_media_info.formats[0] in remote_media_info.formats

        self.local_address: InetAddress = InetAddress(local_conn_info.address, local_media_info.port)
        self.remote_address: InetAddress = InetAddress(remote_conn_info.address, remote_media_info.port)
        self.media_format: MediaFormat = local_media_info.formats[0]

        rtp_map = [rtpmap for rtpmap in local_info.attribute(RtpMap) if rtpmap.media_format == self.media_format][0]
        self.sample_rate: int = rtp_map.sample_rate
        self.audio_channels: int = rtp_map.audio_channels


class CallOutStream(ReadableStream[bytes]):

    def __init__(self):
        self._is_reading = False
        self._callback = None
        self._streams = deque()
        self._current_stream = None

    def start_read(self, callback: Callable[[Optional[bytes]], None]):
        self._is_reading = True
        self._callback = callback

        if len(self._streams) > 0:
            self._start_read_next()

    def attach_stream(self, stream: ReadableStream[bytes]):
        self._streams.append(stream)

        if self._is_reading and self._current_stream is None:
            self._start_read_next()

    def _start_read_next(self):
        if len(self._streams) < 1:
            # we are done
            self._current_stream = None
            self._callback(None)
            return

        stream = self._streams.popleft()
        stream.start_read(self._on_read)
        self._current_stream = stream

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


class CallSession(ABC):

    def __init__(self, info: CallInformation):
        self.info = info
        self._call_in = CallInStream()
        self._call_out = CallOutStream()

    def play_audio_file(self, path: Path):
        self._call_out.attach_stream(WaveFileReadableStream(path, self.info.sample_rate, 2))

    def sink_in_to_file(self, path: Path):
        self._call_in.attach(WaveFileWritableStream(path, self.info.sample_rate, self.info.audio_channels, 2))

    def terminate(self):
        pass


class SessionState(enum.Enum):
    INITIATING = 'init'
    IN_PROGRESS = 'prog'
    TERMINATED = 'term'


class SessionNode(object):

    def __init__(self, session_id: int,
                 state: SessionState = SessionState.INITIATING,
                 session: Optional[CallSession] = None):
        self.session_id = session_id
        self.state = state
        self.session = session

    def attach_session(self, session: CallSession):
        self.session = session
        self.state = SessionState.IN_PROGRESS


class RtpCallSession(CallSession):

    def __init__(self, info: CallInformation, skt: UdpSocket):
        super().__init__(info)
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
        self._stream.start(self._on_stream_complete)

    def _on_stream_complete(self):
        print('_on_stream_complete')

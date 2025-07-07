import io
import random
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from typing import Callable, Optional, List

from ..nio.inet import InetAddress
from ..nio import create_udp_socket, UdpSocket
from ..nio.streams import ReadableStream, WritableStream
from ..rtp.audio_streams import WaveFileWritableStream, WaveFileReadableStream
from ..rtp.codecs import get_encoder, get_decoder
from ..rtp.stream import RtpStream
from ..sdp.message import SdpMessage
from ..common.media_formats import PCMU, MediaFormat
from ..sdp import attributes as sdp_attributes
from ..sdp import fields as sdp_fields
from ..sdp.sdp_types import NetworkType, AddressType, MediaType, MediaProtocol


class RtpRequest(object):

    def __init__(self,
                 session_id: Optional[int] = None,
                 address: Optional[InetAddress] = None,
                 supported_formats: Optional[List[MediaFormat]] = None):
        self.session_id = session_id
        self.address = address
        self.supported_formats = supported_formats

    def parse_from_sdp(self, sdp: SdpMessage):
        originator = sdp.field(sdp_fields.Originator)
        conn_info = sdp.field(sdp_fields.ConnectionInformation)
        media_info = sdp.field(sdp_fields.MediaDescription)

        assert conn_info.address_type == AddressType.IPv4
        assert media_info.media_type == MediaType.AUDIO
        assert media_info.protocol == MediaProtocol.RTP_AVP
        assert len(media_info.formats) > 0
        assert PCMU in media_info.formats
        assert len(sdp.attribute(sdp_attributes.SendRecv)) > 0

        known_rtpmap = [rtpmap.media_format for rtpmap in sdp.attribute(sdp_attributes.RtpMap) if rtpmap.media_format is not None]
        known_fmtp = [fmtp.media_format for fmtp in sdp.attribute(sdp_attributes.Fmtp) if fmtp.media_format is not None]
        assert len(known_rtpmap) > 0
        assert len(known_fmtp) > 0

        self.session_id = originator.session_id
        self.address = InetAddress(conn_info.address, media_info.port)
        self.supported_formats = list(set(known_rtpmap + known_fmtp))

    def compose_to_sdp(self) -> SdpMessage:
        attributes: List[sdp_attributes.Attribute] = [
            sdp_attributes.Rtcp(self.address.port + 1),
            sdp_attributes.SendRecv(),
            sdp_attributes.Ptime(20)
        ]
        attributes.extend([sdp_attributes.RtpMap(f) for f in self.supported_formats])
        attributes.extend([sdp_attributes.Fmtp(f, ['mode-change-capability=2', 'max-red=0']) for f in self.supported_formats])

        # sdp_attributes.RtpMap(MediaFormat.EVENT, 'telephony-event', 8000),
        # sdp_attributes.Fmtp(MediaFormat.EVENT, ['0-16']),

        return SdpMessage(
            fields=[
                sdp_fields.Version(0),
                sdp_fields.Originator(
                    '-',
                    str(self.session_id),
                    '1',
                    NetworkType.IN,
                    AddressType.IPv4,
                    self.address.ip),
                sdp_fields.SessionName('pyims Call'),
                sdp_fields.ConnectionInformation(NetworkType.IN, AddressType.IPv4, self.address.ip),
                sdp_fields.MediaDescription(
                    MediaType.AUDIO,
                    self.address.port,
                    MediaProtocol.RTP_AVP,
                    self.supported_formats),
                sdp_fields.BandwidthInformation('AS', 84),
                sdp_fields.BandwidthInformation('TIAS', 64000),
                sdp_fields.TimeDescription(0, 0)
            ],
            attributes=attributes)


class CallInfo(object):

    def __init__(self, local_address: InetAddress, remote_address: InetAddress, media_format: MediaFormat):
        self.local_address = local_address
        self.remote_address = remote_address
        self.media_format = media_format


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


class CallSession(object):

    def __init__(self, info: CallInfo, skt: UdpSocket):
        self.info = info
        self._call_in = CallInStream()
        self._call_out = CallOutStream()
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

    def play_audio_file(self, path: Path):
        self._call_out.attach_stream(WaveFileReadableStream(path, self.info.media_format))

    def sink_in_to_file(self, path: Path):
        self._call_in.attach(WaveFileWritableStream(path, self.info.media_format))

    def terminate(self):
        self._stream.stop()

    def _on_stream_complete(self):
        print('_on_stream_complete')


class CallHandler(ABC):

    def __init__(self, local_address: str, supported_formats: List[MediaFormat]):
        self._next_session_id = 1
        self._local_address = local_address
        self._supported_formats = supported_formats
        self._sessions = dict()

    def on_invite(self, msg: RtpRequest) -> Optional[RtpRequest]:
        session_id = self._next_session_id
        port = random.randint(40000, 50000)
        local_address = InetAddress(self._local_address, port)
        selected_format = [fmt for fmt in msg.supported_formats if fmt in self._supported_formats][0]

        info = CallInfo(local_address, msg.address, selected_format)
        skt = create_udp_socket(bind_addr=info.local_address)
        session = CallSession(info, skt)
        self._sessions[session_id] = session

        self.call_initiated(session)

        self._next_session_id += 1
        rsp = RtpRequest(session_id, local_address, [selected_format])
        return rsp

    def on_ack(self, local_req: RtpRequest, remote_req: RtpRequest) -> bool:
        selected_format = remote_req.supported_formats[0]
        assert selected_format in self._supported_formats

        info = CallInfo(local_req.address, remote_req.address, selected_format)
        skt = create_udp_socket(bind_addr=info.local_address)
        session = CallSession(info, skt)
        self._sessions[local_req.session_id] = session

        self.call_initiated(session)
        return True

    @abstractmethod
    def call_initiated(self, session: CallSession):
        pass

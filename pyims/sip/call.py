import random
from abc import ABC, abstractmethod
from typing import Optional, List, Callable

from ..common.media_formats import PCMU, MediaFormat
from ..nio.inet import InetAddress
from ..nio.streams import ReadableStream, WritableStream
from ..sdp import attributes as sdp_attributes
from ..sdp import fields as sdp_fields
from ..sdp.message import SdpMessage
from ..sdp.sdp_types import NetworkType, AddressType, MediaType, MediaProtocol


class InviteRequest(object):

    def __init__(self,
                 session_id: int,
                 address: InetAddress,
                 protocol: MediaProtocol,
                 media: MediaType,
                 supported_formats: List[MediaFormat]):
        self.session_id = session_id
        self.address = address
        self.protocol = protocol
        self.media = media
        self.supported_formats = supported_formats

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
                    self.media,
                    self.address.port,
                    self.protocol,
                    self.supported_formats),
                sdp_fields.BandwidthInformation('AS', 84),
                sdp_fields.BandwidthInformation('TIAS', 64000),
                sdp_fields.TimeDescription(0, 0)
            ],
            attributes=attributes)

    @classmethod
    def parse_from_sdp(cls, sdp: SdpMessage) -> 'InviteRequest':
        originator = sdp.field(sdp_fields.Originator)
        conn_info = sdp.field(sdp_fields.ConnectionInformation)
        media_info = sdp.field(sdp_fields.MediaDescription)

        assert conn_info.address_type == AddressType.IPv4
        assert len(media_info.formats) > 0
        assert len(sdp.attribute(sdp_attributes.SendRecv)) > 0

        known_rtpmap = [rtpmap.media_format for rtpmap in sdp.attribute(sdp_attributes.RtpMap) if
                        rtpmap.media_format is not None]
        known_fmtp = [fmtp.media_format for fmtp in sdp.attribute(sdp_attributes.Fmtp) if fmtp.media_format is not None]
        assert len(known_rtpmap) > 0
        assert len(known_fmtp) > 0

        session_id = originator.session_id
        address = InetAddress(conn_info.address, media_info.port)
        protocol = media_info.protocol
        media = media_info.media_type
        supported_formats = known_rtpmap
        return cls(session_id, address, protocol, media, supported_formats)


class CallInfo(object):

    def __init__(self,
                 local_address: InetAddress,
                 remote_address: InetAddress,
                 protocol: MediaProtocol,
                 media_format: MediaFormat):
        self.local_address = local_address
        self.remote_address = remote_address
        self.protocol = protocol
        self.media_format = media_format


class CallSession(ABC):

    def __init__(self, info: CallInfo):
        self.info = info

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def terminate(self):
        pass

    @abstractmethod
    def attach_out(self, stream: ReadableStream[bytes], on_finish: Optional[Callable[[], None]] = None):
        pass

    @abstractmethod
    def attach_in(self, stream: WritableStream[bytes]):
        pass


class CallHandler(ABC):

    def __init__(self, local_address: str, supported_formats: List[MediaFormat]):
        self._next_session_id = 1
        self._local_address = local_address
        self._supported_formats = supported_formats
        self._sessions = dict()

    def create_invite(self, protocol: MediaProtocol, media: MediaType) -> InviteRequest:
        session_id = self._next_session_id
        port = random.randint(40000, 50000)

        self._next_session_id += 1
        return InviteRequest(session_id,
                             InetAddress(self._local_address, port),
                             protocol,
                             media,
                             self._supported_formats)

    def on_invite(self, request: InviteRequest) -> Optional[InviteRequest]:
        selected_format = [fmt for fmt in request.supported_formats if fmt in self._supported_formats][0]
        self._verify_supported(request, selected_format)

        session_id = self._next_session_id
        port = random.randint(40000, 50000)
        local_address = InetAddress(self._local_address, port)

        info = CallInfo(local_address, request.address, request.protocol, selected_format)
        session = self.create_session(info)
        self._sessions[session_id] = session

        self.call_initiated(session)

        self._next_session_id += 1
        rsp = InviteRequest(session_id, local_address, MediaProtocol.RTP_AVP, MediaType.AUDIO, [selected_format])
        return rsp

    def on_ack(self, local_req: InviteRequest, remote_req: InviteRequest) -> bool:
        selected_format = remote_req.supported_formats[0]
        assert selected_format in self._supported_formats
        self._verify_supported(remote_req, selected_format)

        info = CallInfo(local_req.address, remote_req.address, local_req.protocol, selected_format)
        session = self.create_session(info)
        self._sessions[local_req.session_id] = session

        self.call_initiated(session)
        return True

    @abstractmethod
    def call_initiated(self, session: CallSession):
        pass

    @abstractmethod
    def create_session(self, info: CallInfo) -> CallSession:
        pass

    def _verify_supported(self, req: InviteRequest, selected_format: MediaFormat):
        assert req.media == MediaType.AUDIO
        assert req.protocol == MediaProtocol.RTP_AVP
        assert selected_format == PCMU

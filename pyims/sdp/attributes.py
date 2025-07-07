from abc import ABC
from typing import Optional, List, Union

from .sdp_types import TransmitType, TRANSMIT_TYPE_BY_STR
from ..common.media_formats import MediaFormat
from ..rtp.codecs import get_format_identifier, find_format
from ..util import Field


class Attribute(Field, ABC):

    @property
    def name_only(self) -> bool:
        return False


class CustomAttribute(Attribute):

    def __init__(self, name: str, value: Optional[str] = None):
        self._name = name
        self.value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def name_only(self) -> bool:
        return self.value is None

    def parse_from(self, value: str):
        self.value = value

    def compose(self) -> str:
        return self.value


class RtpMap(Attribute):
    __NAME__ = 'rtpmap'

    def __init__(self,
                 media_format: Optional[MediaFormat] = None,
                 format_id: Optional[int] = None,
                 mime_type: Optional[str] = None,
                 sample_rate: Optional[int] = None,
                 audio_channels: Optional[int] = None):
        self.media_format = media_format
        if media_format is not None:
            self.format_id = get_format_identifier(media_format)
            self.mime_type = media_format.name
            self.sample_rate = media_format.sample_rate
            self.audio_channels = media_format.channels
        else:
            self.format_id = format_id
            self.mime_type = mime_type
            self.sample_rate = sample_rate
            self.audio_channels = audio_channels

    def parse_from(self, value: str):
        value = value.split(" ", 1)
        assert len(value) == 2

        self.format_id = int(value[0])

        value = value[1].split('/')
        self.mime_type = value[0]
        self.sample_rate = int(value[1])

        if len(value) > 2:
            self.audio_channels = int(value[2])

        self.media_format = find_format(rtp_id=self.format_id, name=self.mime_type)
        if self.media_format is not None:
            assert not self.audio_channels or self.media_format.channels == self.audio_channels
            assert self.sample_rate == self.media_format.sample_rate

    def compose(self) -> str:
        return f"{self.format_id} {self.mime_type}/{self.sample_rate}" + (f"/{self.audio_channels}" if self.audio_channels is not None else '')


class Fmtp(Attribute):
    __NAME__ = 'fmtp'

    def __init__(self,
                 format_id: Optional[Union[MediaFormat, int]] = None,
                 params: Optional[List[str]] = None):
        self.media_format = format_id if isinstance(format_id, MediaFormat) else None
        self.format_id = format_id
        self.params = params

    def parse_from(self, value: str):
        value = value.split(" ", 1)
        assert len(value) == 2

        self.format_id = int(value[0])
        self.media_format = find_format(rtp_id=self.format_id)
        if self.media_format is not None:
            self.format_id = self.media_format

        self.params = value[1].split(';')

    def compose(self) -> str:
        f_id = get_format_identifier(self.format_id) if isinstance(self.format_id, MediaFormat) else self.format_id
        return f"{f_id} {';'.join(self.params)}"


class Rtcp(Attribute):
    __NAME__ = 'rtcp'

    def __init__(self, port: Optional[int] = None):
        self.port = port

    def parse_from(self, value: str):
        self.port = int(value)

    def compose(self) -> str:
        return str(self.port)


class Ptime(Attribute):
    __NAME__ = 'ptime'

    def __init__(self, time: Optional[int] = None):
        self.time = time

    def parse_from(self, value: str):
        self.time = int(value)

    def compose(self) -> str:
        return str(self.time)


class MaxPtime(Attribute):
    __NAME__ = 'maxptime'

    def __init__(self, time: Optional[int] = None):
        self.time = time

    def parse_from(self, value: str):
        self.time = int(value)

    def compose(self) -> str:
        return str(self.time)


class Transmit(CustomAttribute):

    def __init__(self, transmit_type: TransmitType):
        super().__init__(transmit_type.value)

    @property
    def transmit_type(self) -> TransmitType:
        return TRANSMIT_TYPE_BY_STR[self.name]


class RecvOnly(Transmit):
    __NAME__ = TransmitType.RECVONLY.value

    def __init__(self):
        super().__init__(TransmitType.RECVONLY)


class SendRecv(Transmit):
    __NAME__ = TransmitType.SENDRECV.value

    def __init__(self):
        super().__init__(TransmitType.SENDRECV)


class SendOnly(Transmit):
    __NAME__ = TransmitType.SENDONLY.value

    def __init__(self):
        super().__init__(TransmitType.SENDONLY)


class Inactive(Transmit):
    __NAME__ = TransmitType.INACTIVE.value

    def __init__(self):
        super().__init__(TransmitType.INACTIVE)


ATTRIBUTES = [RtpMap, Fmtp, Rtcp, Ptime, MaxPtime, RecvOnly, SendRecv, SendOnly, Inactive]

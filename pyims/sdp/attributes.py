from abc import ABC
from typing import Optional, List

from .sdp_types import MediaFormat
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
                 mime_type: Optional[str] = None,
                 sample_rate: Optional[int] = None,
                 audio_channels: Optional[int] = None):
        self.media_format = media_format
        self.mime_type = mime_type
        self.sample_rate = sample_rate
        self.audio_channels = audio_channels

    def parse_from(self, value: str):
        value = value.split(" ", 1)
        assert len(value) == 2

        self.media_format = MediaFormat.get(int(value[0]))

        value = value[1].split('/')
        self.mime_type = value[0]
        self.sample_rate = int(value[1])

        if len(value) > 2:
            self.audio_channels = int(value[2])

    def compose(self) -> str:
        return f"{self.media_format.value} {self.mime_type}/{self.sample_rate}" + (f"/{self.audio_channels}" if self.audio_channels is not None else '')


class Fmtp(Attribute):
    __NAME__ = 'fmtp'

    def __init__(self,
                 media_format: Optional[MediaFormat] = None,
                 params: Optional[List[str]] = None):
        self.media_format = media_format
        self.params = params

    def parse_from(self, value: str):
        value = value.split(" ", 1)
        assert len(value) == 2

        self.media_format = MediaFormat.get(int(value[0]))
        self.params = value[1].split(';')

    def compose(self) -> str:
        return f"{self.media_format.value} {';'.join(self.params)}"


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


class RecvOnly(CustomAttribute):

    def __init__(self):
        super().__init__('recvonly')


class SendRecv(CustomAttribute):

    def __init__(self):
        super().__init__('sendrecv')


ATTRIBUTES = [RtpMap, Fmtp, Rtcp, Ptime, RecvOnly, SendRecv]

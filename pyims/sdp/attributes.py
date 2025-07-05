from abc import ABC
from typing import Optional, List

from .sdp_types import MediaFormat
from ..util import Field


class Attribute(Field, ABC):
    pass


class CustomAttribute(Attribute):

    def __init__(self, name: str, value: str):
        self._name = name
        self.value = value

    @property
    def name(self) -> str:
        return self._name

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
        return f"{self.media_format} {';'.join(self.params)}"


ATTRIBUTES = [RtpMap, Fmtp]

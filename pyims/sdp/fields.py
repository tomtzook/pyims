from abc import ABC
from typing import Optional, List

from .sdp_types import (
    NetworkType, AddressType, MediaType, MediaProtocol,
    MEDIA_TYPE_BY_STR, MEDIA_PROTOCOL_BY_STR, ADDRESS_TYPE_BY_STR, NETWORK_TYPE_BY_STR, MediaFormat
)
from .attributes import Attribute, ATTRIBUTES, CustomAttribute
from ..util import Field


class SdpField(Field, ABC):

    @property
    def can_have_multiple(self) -> bool:
        return False


class Version(SdpField):
    __NAME__ = 'v'

    def __init__(self, version: Optional[int] = None):
        self.version = version

    def parse_from(self, value: str):
        self.version = int(value)

    def compose(self) -> str:
        return str(self.version)


class SessionName(SdpField):
    __NAME__ = 's'

    def __init__(self, session_name: Optional[str] = None):
        self.session_name = session_name

    def parse_from(self, value: str):
        self.session_name = value

    def compose(self) -> str:
        return self.session_name


class ConnectionInformation(SdpField):
    __NAME__ = 'c'

    def __init__(self,
                 network_type: Optional[NetworkType] = None,
                 address_type: Optional[AddressType] = None,
                 address: Optional[str] = None):
        self.network_type = network_type
        self.address_type = address_type
        self.address = address

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) == 3

        self.network_type = NETWORK_TYPE_BY_STR[value[0]]
        self.address_type = ADDRESS_TYPE_BY_STR[value[1]]
        self.address = value[2]

    def compose(self) -> str:
        return " ".join([self.network_type.value, self.address_type.value, self.address])


class Originator(SdpField):
    __NAME__ = 'o'

    def __init__(self,
                 username: Optional[str] = None,
                 session_id: Optional[str] = None,
                 session_version: Optional[str] = None,
                 network_type: Optional[NetworkType] = None,
                 address_type: Optional[AddressType] = None,
                 address: Optional[str] = None):
        self.username = username
        self.session_id = session_id
        self.session_version = session_version
        self.network_type = network_type
        self.address_type = address_type
        self.address = address

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) == 6

        self.username = value[0]
        self.session_id = value[1]
        self.session_version = value[2]
        self.network_type = NETWORK_TYPE_BY_STR[value[3]]
        self.address_type = ADDRESS_TYPE_BY_STR[value[4]]
        self.address = value[5]

    def compose(self) -> str:
        return " ".join([self.username, self.session_id, self.session_version, self.network_type.value, self.address_type.value, self.address])


class MediaDescription(SdpField):
    __NAME__ = 'm'

    def __init__(self,
                 media_type: Optional[MediaType] = None,
                 port: Optional[int] = None,
                 protocol: Optional[MediaProtocol] = None,
                 formats: Optional[List[MediaFormat]] = None):
        self.media_type = media_type
        self.port = port
        self.protocol = protocol
        self.formats = formats

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) >= 3

        self.media_type = MEDIA_TYPE_BY_STR[value[0]]
        self.port = int(value[1])
        self.protocol = MEDIA_PROTOCOL_BY_STR[value[2]]

        if len(value) > 3:
            self.formats = [MediaFormat.get(int(e)) for e in value[3:]]
        else:
            self.formats = None

    def compose(self) -> str:
        lst = [self.media_type.value, str(self.port), self.protocol.value]
        if self.formats:
            lst.extend([str(e.value) for e in self.formats])

        return " ".join(lst)


class TimeDescription(SdpField):
    __NAME__ = 't'

    def __init__(self, start_time: Optional[int] = None, stop_time: Optional[int] = None):
        self.start_time = start_time
        self.stop_time = stop_time

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) == 2

        self.start_time = int(value[0])
        self.stop_time = int(value[1])

    def compose(self) -> str:
        return f"{self.start_time} {self.stop_time}"


class AttributeField(SdpField):
    __NAME__ = 'a'

    def __init__(self, attribute: Optional[Attribute] = None):
        self.attribute = attribute

    @property
    def can_have_multiple(self) -> bool:
        return True

    def parse_from(self, value: str):
        value = value.split(':', 1)

        self.attribute = None
        for attr in ATTRIBUTES:
            attr = attr()
            if attr.name == value[0]:
                attr.parse_from(value[1])
                self.attribute = attr
                break

        if self.attribute is None:
            self.attribute = CustomAttribute(value[0], value[1])

    def compose(self) -> str:
        return f"{self.attribute.name}:{self.attribute.compose()}"


class BandwidthInformation(SdpField):
    __NAME__ = 'b'

    def __init__(self,
                 modifier: Optional[str] = None,
                 value: Optional[int] = None):
        self.modifier = modifier
        self.value = value

    @property
    def can_have_multiple(self) -> bool:
        return True

    def parse_from(self, value: str):
        value = value.split(":", 1)
        self.modifier = value[0]
        self.value = int(value[1])

    def compose(self) -> str:
        return f"{self.modifier}:{self.value}"


FIELDS = [Version, SessionName, ConnectionInformation, Originator, MediaDescription, TimeDescription, AttributeField, BandwidthInformation]

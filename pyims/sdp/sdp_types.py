import enum


class NetworkType(enum.Enum):
    IN = 'IN'


class AddressType(enum.Enum):
    IPv4 = 'IP4'


class MediaType(enum.Enum):
    AUDIO = 'audio'


class MediaProtocol(enum.Enum):
    RTP_AVP = 'RTP/AVP'


class MediaFormat(enum.Enum):
    def __new__(
        cls,
        value: int,
        description: str = "",
        clock: int = 0,
        channel: int = 0,
    ):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        obj.rate = clock
        obj.channel = channel
        return obj

    @classmethod
    def get(cls, value: int):
        for e in list(cls):
            if e.value == value:
                return e

        return cls(value)

    PCMU = 0, "PCMU", 8000, 1


NETWORK_TYPE_BY_STR = {e.value: e for e in list(NetworkType)}
ADDRESS_TYPE_BY_STR = {e.value: e for e in list(AddressType)}
MEDIA_TYPE_BY_STR = {e.value: e for e in list(MediaType)}
MEDIA_PROTOCOL_BY_STR = {e.value: e for e in list(MediaProtocol)}
MEDIA_FORMAT_BY_INT = {e.value: e for e in list(MediaFormat)}

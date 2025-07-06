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
        clock: int = 0,
        channels: int = 0,
    ):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.rate = clock
        obj.channels = channels
        return obj

    @staticmethod
    def get(value: int):
        for e in list(MediaFormat):
            if e.value == value:
                return e

        obj = object.__new__(MediaFormat)
        obj._value_ = value
        obj.rate = 0
        obj.channels = 0
        return obj

    # see https://datatracker.ietf.org/doc/html/rfc3551 tables 4 and 5
    PCMU = 0, 8000, 1
    GSM = 3, 8000, 1
    G723 = 4, 8000, 1
    DVI4_8000 = 5, 8000, 1
    DVI4_16000 = 6, 16000, 1
    LPC = 7, 8000, 1
    PCMA = 8, 8000, 1
    G722 = 9, 8000, 1
    L16_2 = 10, 44100, 2
    L16 = 11, 44100, 1
    QCELP = 12, 8000, 1
    CN = 13, 8000, 1
    OPUS = 107, 48000, 2
    MPA = 14, 90000, 0
    G728 = 15, 8000, 1
    DVI4_11025 = 16, 11025, 1
    DVI4_22050 = 17, 22050, 1
    G729 = 18, 8000, 1
    CELB = 25, 90000, 0
    JPEG = 26, 90000, 0
    NV = 28, 90000, 0
    H261 = 31, 90000, 0
    MPV = 32, 90000, 0
    MP2T = 33, 90000, 1
    H263 = 34, 90000, 0
    EVENT = 121, 8000, 0


class TransmitType(enum.Enum):
    RECVONLY = "recvonly"
    SENDRECV = "sendrecv"
    SENDONLY = "sendonly"
    INACTIVE = "inactive"


NETWORK_TYPE_BY_STR = {e.value: e for e in list(NetworkType)}
ADDRESS_TYPE_BY_STR = {e.value: e for e in list(AddressType)}
MEDIA_TYPE_BY_STR = {e.value: e for e in list(MediaType)}
MEDIA_PROTOCOL_BY_STR = {e.value: e for e in list(MediaProtocol)}
MEDIA_FORMAT_BY_INT = {e.value: e for e in list(MediaFormat)}
TRANSMIT_TYPE_BY_STR = {e.value: e for e in list(TransmitType)}

import enum

from ..common.media_formats import MediaType


class NetworkType(enum.Enum):
    IN = 'IN'


class AddressType(enum.Enum):
    IPv4 = 'IP4'


class MediaProtocol(enum.Enum):
    RTP_AVP = 'RTP/AVP'


class TransmitType(enum.Enum):
    RECVONLY = "recvonly"
    SENDRECV = "sendrecv"
    SENDONLY = "sendonly"
    INACTIVE = "inactive"


NETWORK_TYPE_BY_STR = {e.value: e for e in list(NetworkType)}
ADDRESS_TYPE_BY_STR = {e.value: e for e in list(AddressType)}
MEDIA_TYPE_BY_STR = {e.value: e for e in list(MediaType)}
MEDIA_PROTOCOL_BY_STR = {e.value: e for e in list(MediaProtocol)}
TRANSMIT_TYPE_BY_STR = {e.value: e for e in list(TransmitType)}

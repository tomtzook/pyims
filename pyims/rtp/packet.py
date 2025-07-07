import struct
from typing import List, Optional

from .codecs import MediaFormat, get_format_identifier, find_format


class RtpPacket(object):
    HEADER_FORMAT = '!BBHII'
    HEADER_LENGTH = 12

    def __init__(
            self,
            payload_format: MediaFormat,
            seq_num: int,
            timestamp: int,
            ssrc: int,
            payload: bytes,
            marker: bool = False,
            csrc: Optional[List[int]] = None
    ):
        self.version = 2
        self.has_padding = False
        self.has_extension = False
        self.marker = marker
        self.csrc = csrc or []

        self.payload_format = payload_format
        self.seq_num = seq_num
        self.timestamp = timestamp
        self.ssrc = ssrc
        self.payload = payload

    def compose(self) -> bytes:
        pt_id = get_format_identifier(self.payload_format)
        assert pt_id is not None

        formatb = chr(pt_id).encode('utf-8')
        assert len(formatb) == 1

        b1 = (self.version & 3) << 6
        b1 |= ((1 if self.has_padding else 0) & 1) << 5
        b1 |= ((1 if self.has_extension else 0) & 1) << 4
        b1 |= (len(self.csrc)) & 0x0f

        b2 = formatb[0] & 0x7f
        b2 |= ((1 if self.has_extension else 0) & 1) << 7

        header = struct.pack(self.HEADER_FORMAT, b1, b2, self.seq_num, self.timestamp, self.ssrc)
        for c in self.csrc:
            header += struct.pack('!I', c)
        return header + self.payload


def parse_rtp_packet(data: bytes) -> RtpPacket:
    header_size = struct.calcsize(RtpPacket.HEADER_FORMAT)
    header, payload = data[:header_size], data[header_size:]
    b1, b2, seq_num, timestamp, ssrc = struct.unpack(RtpPacket.HEADER_FORMAT, header)

    version = (b1 >> 6) & 3
    padding = (b1 >> 5) & 1
    extension = (b1 >> 4) & 1
    cc = b1 & 0xf
    marker = (b2 >> 7) & 1
    pt = b2 & 0x7f

    assert version == 2
    assert not extension

    pt_obj = find_format(rtp_id=pt)
    assert pt_obj is not None, "unknown rtp format"

    csrc = []
    for i in range(0, cc):
        pos = 4 * i
        csrc.append(struct.unpack_from('!I', payload, pos)[0])

    pos = cc * 4
    if padding:
        padding_len = payload[-1]
        if not padding_len or padding_len > len(data) - pos:
            raise ValueError("RTP packet padding length is invalid")
        payload = payload[pos:-padding_len]
    else:
        payload = payload[pos:]

    return RtpPacket(
        pt_obj,
        seq_num,
        timestamp,
        ssrc,
        payload,
        marker=marker,
        csrc=csrc
    )

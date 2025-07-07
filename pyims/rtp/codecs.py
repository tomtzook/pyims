from abc import ABC, abstractmethod
import audioop
from typing import Optional, Tuple, List, Type

from ..common.media_formats import MediaFormat, PCMU, PCMA


class Encoder(ABC):

    @abstractmethod
    def encode(self, data: bytes) -> bytes:
        pass


class Decoder(ABC):

    @abstractmethod
    def decode(self, data: bytes) -> bytes:
        pass


class PcmuEncoder(Encoder):

    def encode(self, data: bytes) -> bytes:
        return audioop.lin2ulaw(data, PCMU.sample_width)


class PcmuDecoder(Decoder):

    def decode(self, data: bytes) -> bytes:
        return audioop.ulaw2lin(data, PCMU.sample_width)


class PcmaEncoder(Encoder):

    def encode(self, data: bytes) -> bytes:
        return audioop.lin2alaw(data, PCMA.sample_width)


class PcmaDecoder(Decoder):

    def decode(self, data: bytes) -> bytes:
        return audioop.alaw2lin(data, PCMA.sample_width)


# see https://datatracker.ietf.org/doc/html/rfc3551 tables 4 and 5
# format,id,encoder,decoder
RTP_MEDIA_FORMATS: List[Tuple[MediaFormat, int, Type[Encoder], Type[Decoder]]] = [
    (PCMU, 0, PcmuEncoder, PcmuDecoder),
    (PCMA, 8, PcmaEncoder, PcmaDecoder),
]


def register_format_to_id(media_format: MediaFormat, rtp_id: int,
                          encoder: Optional[Type[Encoder]] = None,
                          decoder: Optional[Type[Decoder]] = None):
    for f in RTP_MEDIA_FORMATS:
        c_mformat = f[0]
        c_id = f[1]

        if media_format.name == c_mformat.name:
            if c_id == rtp_id:
                return
            if c_id is None:
                f[1] = rtp_id
                break
            if c_id != rtp_id:
                raise ValueError(f"another format \"{c_mformat.name}\"is already using the ID {rtp_id}")

    # format isn't in list
    assert encoder is not None and decoder is not None, "encoder and decoder required for new format"
    RTP_MEDIA_FORMATS.append((media_format, rtp_id, encoder, decoder))


def find_format(rtp_id: Optional[int] = None, name: Optional[str] = None) -> Optional[MediaFormat]:
    rtp_media_formats_by_id = {f[1]: f[0] for f in RTP_MEDIA_FORMATS}
    rtp_media_formats_by_name = {f[0].name: f[0] for f in RTP_MEDIA_FORMATS}

    assert rtp_id is not None or name is not None
    if rtp_id is not None and rtp_id in rtp_media_formats_by_id:
        return rtp_media_formats_by_id[rtp_id]
    if name is not None and name in rtp_media_formats_by_name:
        return rtp_media_formats_by_name[name]

    return None


def get_format_identifier(media_format: MediaFormat) -> Optional[int]:
    rtp_media_format_id_by_name = {f[0].name: f[1] for f in RTP_MEDIA_FORMATS}

    if media_format.name in rtp_media_format_id_by_name:
        return rtp_media_format_id_by_name[media_format.name]

    return None


def get_encoder(media_format: MediaFormat) -> Encoder:
    encoders = {f[0]: f[2] for f in RTP_MEDIA_FORMATS}

    if media_format in encoders:
        return encoders[media_format]()

    raise ValueError('Unsupported format: ' + media_format.name)


def get_decoder(media_format: MediaFormat) -> Decoder:
    decoders = {f[0]: f[3] for f in RTP_MEDIA_FORMATS}

    if media_format in decoders:
        return decoders[media_format]()

    raise ValueError('Unsupported format: ' + media_format.name)

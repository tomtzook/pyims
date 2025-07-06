from abc import ABC, abstractmethod
import audioop

from ..sdp.sdp_types import MediaFormat


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
        return audioop.lin2ulaw(data, 2)


class PcmuDecoder(Decoder):

    def decode(self, data: bytes) -> bytes:
        return audioop.ulaw2lin(data, 2)


class PcmaEncoder(Encoder):

    def encode(self, data: bytes) -> bytes:
        return audioop.lin2alaw(data, 2)


class PcmaDecoder(Decoder):

    def decode(self, data: bytes) -> bytes:
        return audioop.alaw2lin(data, 2)


def get_encoder(media_format: MediaFormat) -> Encoder:
    encoders = {
        MediaFormat.PCMU: PcmuEncoder,
        MediaFormat.PCMA: PcmaEncoder
    }

    if media_format in encoders:
        return encoders[media_format]()

    raise ValueError('Unsupported format: ' + media_format.name)


def get_decoder(media_format: MediaFormat) -> Decoder:
    decoders = {
        MediaFormat.PCMU: PcmuDecoder,
        MediaFormat.PCMA: PcmaDecoder
    }

    if media_format in decoders:
        return decoders[media_format]()

    raise ValueError('Unsupported format: ' + media_format.name)

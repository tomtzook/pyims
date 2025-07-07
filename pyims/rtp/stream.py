from typing import Tuple, Optional, Callable
import logging

from .codecs import Encoder, Decoder
from .packet import RtpPacket, parse_rtp_packet
from ..nio.inet import InetAddress
from ..nio.sockets import UdpSocket
from ..nio.streams import ReadableStream, WritableStream
from .codecs import MediaFormat

logger = logging.getLogger('pyims.rtp.stream')


class RtpStream(object):

    def __init__(self,
                 skt: UdpSocket,
                 source: ReadableStream[bytes],
                 sink: WritableStream[bytes],
                 remote_address: InetAddress,
                 media_format: MediaFormat,
                 encoder: Encoder,
                 decoder: Decoder,
                 ssrc: int):
        self._socket = skt
        self._source = source
        self._sink = sink
        self._remote = remote_address
        self._format = media_format
        self._encoder = encoder
        self._decoder = decoder
        self._ssrc = ssrc

        self._seq_num: int = 0
        self._timestamp: int = 0
        self._complete_callback = None

    def start(self, complete_callback: Callable[[], None]):
        self._complete_callback = complete_callback
        self._socket.start_read(self._on_remote_data)
        self._source.start_read(self._on_local_data)

    def _on_local_data(self, data: Optional[bytes]):
        if data is None:
            logger.info('[RTP] local EOF')
            if self._complete_callback:
                self._complete_callback()
            return

        logger.info('[RTP] new data to send (len %d)', len(data))

        payload = self._encoder.encode(data)
        packet = RtpPacket(
            self._format,
            self._seq_num,
            self._timestamp,
            self._ssrc,
            payload
        )
        self._socket.write((self._remote, packet.compose()))

        self._seq_num = (self._seq_num + 1) % 65535
        self._timestamp = (self._timestamp + len(payload)) % 4294967295

    def _on_remote_data(self, data_p: Optional[Tuple[InetAddress, bytes]]):
        if data_p is None:
            logger.info('[RTP] remote EOF')
            self._sink.write_done()
            return

        sender, data = data_p

        logger.info('[RTP] new data received (len %d)', len(data))
        packet = parse_rtp_packet(data)

        if packet.payload_format != self._format:
            return

        # todo: jitter packet
        payload = self._decoder.decode(packet.payload)
        self._sink.write(payload)

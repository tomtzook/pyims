import time
from typing import Tuple, Optional

from .codecs import Encoder, Decoder
from .rtp_types import RtpPacket, parse_rtp_packet
from ..nio.inet import InetAddress
from ..nio.sockets import UdpSocket
from ..nio.streams import ReadableStream, WritableStream
from ..sdp.sdp_types import MediaFormat


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

        self._socket.start_read(self._on_remote_data)
        self._source.start_read(self._on_local_data)

    def _loop_send(self):
        while True:
            start = time.monotonic_ns()

            payload = self._source.query()
            if payload is None:
                time.sleep(0.02)
                continue

            payload = self._encoder.encode(payload)
            packet = RtpPacket(
                self._format,
                self._seq_num,
                self._timestamp,
                self._ssrc,
                payload
            )
            # TODO: WAIT READ FINISH
            self._socket.write((self._remote, packet.compose()))

            delay = (1 / self._format.rate) * 160
            proc_time = (time.monotonic_ns() - start) / 1e9
            sleep_time = delay - proc_time
            sleep_time = max(0, sleep_time)

            self._seq_num = (self._seq_num + 1) % 65535
            self._timestamp = (self._timestamp + len(payload)) % 4294967295

            time.sleep(sleep_time)

    def _on_local_data(self, data: Optional[bytes]):
        if data is None:
            # TODO: END OF STREAM
            return

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
            # TODO: END OF STREAM
            return

        sender, data = data_p
        if sender != self._remote:
            return

        packet = parse_rtp_packet(data)

        if packet.payload_format != self._format:
            return

        # todo: jitter packet
        payload = self._decoder.decode(packet.payload)
        self._sink.write(payload)

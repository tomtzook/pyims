from abc import ABC, abstractmethod
from typing import Optional, List

from pyims.sip.message import Message
from pyims.sip.parser import parse
from pyims.sip.sip_socket import SipSocket, connect_tcp


class Transport(ABC):

    def __init__(self):
        self._skt: Optional[SipSocket] = None

    def receive(self) -> List[Message]:
        skt = self._get_or_connect_socket()
        # todo: buffer data
        data = skt.read()
        return self._parse_messages(data)

    def send(self, message: Message):
        skt = self._get_or_connect_socket()
        skt.write(message.compose().encode('utf-8'))

    def close(self):
        if self._skt is not None:
            self._skt.close()
            self._skt = None

    def _get_or_connect_socket(self) -> SipSocket:
        if self._skt is not None:
            return self._skt

        skt = self._connect_socket()
        self._skt = skt
        return skt

    @abstractmethod
    def _connect_socket(self) -> SipSocket:
        pass

    @staticmethod
    def _parse_messages(data: bytes) -> List[Message]:
        data = data.decode('utf-8')

        messages = []
        start = 0

        while start < len(data):
            end_of_headers = data.find('\r\n\r\n', start)
            if end_of_headers < 0:
                break

            message = parse(data, start)
            messages.append(message)

            start = end_of_headers + len(message.body) + 1

        return messages


class TcpTransport(Transport):

    def __init__(self, local_address: str, local_port: int, remote_address: str, remote_port: int):
        super().__init__()
        self._local_address = local_address
        self._local_port = local_port
        self._remote_address = remote_address
        self._remote_port = remote_port

    def _connect_socket(self) -> SipSocket:
        return connect_tcp(self._local_address, self._local_port, self._remote_address, self._remote_port)

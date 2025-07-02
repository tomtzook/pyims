from abc import ABC, abstractmethod

from pyims.sip.sip_socket import SipSocket, connect_tcp


class Transport(ABC):

    @abstractmethod
    def connect_socket(self) -> SipSocket:
        pass


class TcpTransport(Transport):

    def __init__(self, local_address: str, local_port: int,
                 remote_address: str, remote_port: int):
        self._local_address = local_address
        self._local_port = local_port
        self._remote_address = remote_address
        self._remote_port = remote_port

    def connect_socket(self) -> SipSocket:
        return connect_tcp(self._local_address, self._local_port, self._remote_address, self._remote_port)

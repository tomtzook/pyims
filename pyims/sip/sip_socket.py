from abc import ABC, abstractmethod
import socket


class SipSocket(ABC):

    @abstractmethod
    def read(self) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes):
        pass

    @abstractmethod
    def close(self):
        pass


class SipTcpSocket(SipSocket):

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    def bind(self, address: str, port: int):
        self._socket.bind((address, port))

    def connect(self, address: str, port: int):
        self._socket.connect((address, port))

    def read(self) -> bytes:
        return self._socket.recv(4096)

    def write(self, data: bytes):
        self._socket.sendall(data)

    def close(self):
        self._socket.close()
        self._socket = None


def connect_tcp(local_address: str, local_port: int, remote_address: str, remote_port: int) -> SipSocket:
    sok = SipTcpSocket()
    sok.bind(local_address, local_port)
    sok.connect(remote_address, remote_port)

    return sok

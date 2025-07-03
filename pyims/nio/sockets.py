import socket
from typing import Optional, Callable

from pyims.nio.selector import Selector, TcpRegistration, TcpServerRegistration


class TcpSocket(object):
    STATE_UNCONNECTED = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2

    def __init__(self, skt: Optional[socket.socket] = None):
        if skt is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        else:
            self._socket = skt

        self._socket.setblocking(False)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._registration = TcpRegistration(self._socket, self._on_read, self._on_connect, self._on_error, already_connected=skt is not None)
        self._state = self.STATE_UNCONNECTED if skt is None else self.STATE_CONNECTED

        self._read_callback = None
        self._connect_callback = None

    def register_to(self, selector: Selector):
        selector.register(self._registration)

    def bind(self, address: str, port: int):
        assert self._state == self.STATE_UNCONNECTED, "cannot bind if connected or connecting"

        self._socket.bind((address, port))

    def connect(self, address: str, port: int, callback: Callable[[], None]):
        assert self._state == self.STATE_UNCONNECTED, "connection already initiated"

        errno = self._socket.connect_ex((address, port))
        if errno != 115:  # E_WOULDBLOCK
            raise OSError(errno)

        self._connect_callback = callback
        self._registration.mark_state_connecting()

    def start_read(self, callback: Callable[[bytes], None]):
        assert self._state == self.STATE_CONNECTED, "cannot read until connected"
        self._read_callback = callback
        self._registration.start_read()

    def write(self, data: bytes):
        assert self._state == self.STATE_CONNECTED, "cannot write until connected"
        self._registration.enqueue_send(data)

    def close(self):
        self._socket.close()

    def _on_read(self, data: bytes):
        if self._read_callback is not None:
            self._read_callback(data)

    def _on_connect(self):
        self._state = self.STATE_CONNECTED
        if self._connect_callback is not None:
            self._connect_callback()
            self._connect_callback = None

    def _on_error(self, ex: Exception):
        print(ex)
        self.close()


class TcpServerSocket(object):

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._socket.setblocking(False)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._registration = TcpServerRegistration(self._socket, self._on_connect, self._on_error)
        self._on_connect_callback = None

    def register_to(self, selector: Selector):
        selector.register(self._registration)

    def bind(self, address: str, port: int):
        self._socket.bind((address, port))

    def listen(self, backlog: int, callback: Callable[[TcpSocket], None]):
        self._socket.listen(backlog)
        self._on_connect_callback = callback
        self._registration.start_listening()

    def close(self):
        self._socket.close()

    def _on_connect(self):
        client, address = self._socket.accept()
        # noinspection PyTypeChecker
        new_skt = TcpSocket(client)

        if self._on_connect_callback is not None:
            self._on_connect_callback(new_skt)

    def _on_error(self, ex: Exception):
        print(ex)
        self.close()

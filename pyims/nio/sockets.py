import socket
import logging
from typing import Optional, Callable

from .inet import InetAddress
from .selector import Selector, TcpRegistration, TcpServerRegistration, UdpRegistration

logger = logging.getLogger('pyims.nio.sockets')


class TcpSocket(object):
    STATE_UNCONNECTED = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2

    def __init__(self, skt: Optional[socket.socket] = None,
                 local_address: Optional[InetAddress] = None,
                 remote_address: Optional[InetAddress] = None):
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
        self._local_address: Optional[InetAddress] = local_address
        self._remote_address: Optional[InetAddress] = remote_address

    @property
    def local_address(self) -> InetAddress:
        assert self._local_address is not None, "not bound to a local address"
        return self._local_address

    @property
    def remote_address(self) -> InetAddress:
        assert self._remote_address is not None, "not connected to remote"
        assert self._state == self.STATE_CONNECTED, "not connected"
        return self._remote_address

    def register_to(self, selector: Selector):
        selector.register(self._registration)

    def bind(self, address: InetAddress):
        assert self._state == self.STATE_UNCONNECTED, "cannot bind if connected or connecting"
        logger.info('[Socket, %d] [TCP-C] Binding to %s', self._socket.fileno(), address)
        self._socket.bind((address.ip, address.port))
        self._local_address = address

    def connect(self, address: InetAddress, callback: Callable[[], None]):
        assert self._state == self.STATE_UNCONNECTED, "connection already initiated"

        logger.info('[Socket, %d] [TCP-C] Starting connect to %s', self._socket.fileno(), address)
        errno = self._socket.connect_ex((address.ip, address.port))
        if errno != 115:  # E_WOULDBLOCK
            raise OSError(errno)

        self._remote_address = address
        self._connect_callback = callback
        self._registration.mark_state_connecting()

    def start_read(self, callback: Callable[[bytes], None]):
        assert self._state == self.STATE_CONNECTED, "cannot read until connected"
        logger.info('[Socket, %d] [TCP-C] Starting auto read', self._socket.fileno())
        self._read_callback = callback
        self._registration.start_read()

    def write(self, data: bytes):
        assert self._state == self.STATE_CONNECTED, "cannot write until connected"
        logger.info('[Socket, %d] [TCP-C] Writing data (len %d)', self._socket.fileno(), len(data))
        self._registration.enqueue_send(data)

    def close(self):
        logger.info('[Socket, %d] [TCP-C] Closing', self._socket.fileno())
        self._socket.close()

    def _on_read(self, data: bytes):
        logger.debug('[Socket, %d] [TCP-C] On Read data (len %d)', self._socket.fileno(), len(data))
        if self._read_callback is not None:
            self._read_callback(data)

    def _on_connect(self):
        logger.debug('[Socket, %d] [TCP-C] On Connect', self._socket.fileno())
        self._state = self.STATE_CONNECTED
        if self._connect_callback is not None:
            self._connect_callback()
            self._connect_callback = None

    def _on_error(self, ex: Exception):
        logger.exception('[Socket, %d] [TCP-C] On Error', self._socket.fileno(), exc_info=ex)
        self.close()

    def __del__(self):
        self.close()


class TcpServerSocket(object):

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._socket.setblocking(False)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._registration = TcpServerRegistration(self._socket, self._on_connect, self._on_error)
        self._on_connect_callback = None
        self._local_address: Optional[InetAddress] = None

    @property
    def local_address(self) -> InetAddress:
        assert self._local_address is not None, "not bound to a local address"
        return self._local_address

    def register_to(self, selector: Selector):
        selector.register(self._registration)

    def bind(self, address: InetAddress):
        logger.info('[Socket, %d] [TCP-S] Binding to %s', self._socket.fileno(), address)
        self._socket.bind((address.ip, address.port))
        self._local_address = address

    def listen(self, backlog: int, callback: Callable[[TcpSocket], None]):
        logger.info('[Socket, %d] [TCP-S] Starting listen (backlog %d)', self._socket.fileno(), backlog)
        self._socket.listen(backlog)
        self._on_connect_callback = callback
        self._registration.start_listening()

    def close(self):
        logger.info('[Socket, %d] [TCP-S] Closing', self._socket.fileno())
        self._socket.close()

    def _on_connect(self):
        logger.debug('[Socket, %d] [TCP-S] On Connect', self._socket.fileno())
        client, remote_address = self._socket.accept()
        local_address = InetAddress(*client.getsockname())
        remote_address = InetAddress(*remote_address)
        # noinspection PyTypeChecker
        new_skt = TcpSocket(client, local_address=local_address, remote_address=remote_address)

        logger.info('[Socket, %d] [TCP-S] New Client Accepted (fd %d, addr %s)', self._socket.fileno(), client.fileno(), remote_address)

        if self._on_connect_callback is not None:
            self._on_connect_callback(new_skt)

    def _on_error(self, ex: Exception):
        logger.exception('[Socket, %d] [TCP-S] On Error', self._socket.fileno(), exc_info=ex)
        self.close()

    def __del__(self):
        self.close()


class UdpSocket(object):

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socket.setblocking(False)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._registration = UdpRegistration(self._socket, self._on_read, self._on_error)

        self._read_callback = None
        self._connect_callback = None
        self._local_address: Optional[InetAddress] = None

    @property
    def local_address(self) -> InetAddress:
        assert self._local_address is not None, "not bound to a local address"
        return self._local_address

    def register_to(self, selector: Selector):
        selector.register(self._registration)

    def bind(self, address: InetAddress):
        logger.info('[Socket, %d] [UDP] Binding to %s', self._socket.fileno(), address)
        self._socket.bind((address.ip, address.port))
        self._local_address = address

    def start_read(self, callback: Callable[[InetAddress, bytes], None]):
        logger.info('[Socket, %d] [UDP] Starting auto read', self._socket.fileno())
        self._read_callback = callback
        self._registration.start_read()

    def write(self, dest: InetAddress, data: bytes):
        logger.info('[Socket, %d] [UDP] Writing data (dest %s, len %d)', self._socket.fileno(), dest, len(data))
        self._registration.enqueue_send(dest, data)

    def close(self):
        logger.info('[Socket, %d] [UDP] Closing', self._socket.fileno())
        self._socket.close()

    def _on_read(self, sender: InetAddress, data: bytes):
        logger.debug('[Socket, %d] [UDP] On Read data (sender %s, len %d)', self._socket.fileno(), sender, len(data))
        if self._read_callback is not None:
            self._read_callback(sender, data)

    def _on_error(self, ex: Exception):
        logger.exception('[Socket, %d] [UDP] On Error', self._socket.fileno(), exc_info=ex)
        self.close()

    def __del__(self):
        self.close()

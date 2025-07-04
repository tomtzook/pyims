from collections import deque
from typing import Optional, List, Tuple, Callable
import logging
import threading
import io

from pyims.nio.inet import InetAddress
from pyims.nio.selector import Selector
from pyims.nio.sockets import TcpSocket
from pyims.sip.message import Message
from pyims.sip.parser import parse


logger = logging.getLogger('pyims.sip.sockets')


class SipTcpSocket(object):

    def __init__(self):
        self._lock = threading.RLock()
        self._socket: Optional[TcpSocket] = None
        self._is_connected: bool = False
        self._read_event = threading.Event()
        self._read_buff = io.BytesIO()
        self._in_message_queue: deque[Message] = deque()
        self._out_message_queue: deque[Message] = deque()
        self._on_next_read = None

    def send(self, message: Message):
        with self._lock:
            logger.debug('[SIP] [TCP-C] User sending new message %s', message.compose())

            if self._socket is None:
                return

            if not self._is_connected:
                self._out_message_queue.append(message)
            else:
                self._socket.write(message.compose().encode("utf-8"))

    def await_message(self, timeout: float) -> Optional[Message]:
        with self._lock:
            if self._socket is None:
                return None

            if len(self._in_message_queue) > 0:
                return self._in_message_queue.popleft()

        if self._read_event.wait(timeout):
            self._read_event.clear()

            with self._lock:
                return self._in_message_queue.popleft()
        else:
            return None

    def close(self):
        with self._lock:
            if self._socket is not None:
                self._socket.close()
                self._socket = None

    def _attach_socket(self, socket: TcpSocket, connected: bool = False, on_next_read: Callable[[], None] = None):
        with self._lock:
            self._socket = socket
            self._on_next_read = on_next_read

        if connected:
            self._on_connect()

    def _on_connect(self):
        with self._lock:
            if self._socket is None:
                return

            logger.info('[SIP] [TCP-C] Socket finished connect')

            self._is_connected = True
            self._read_buff.truncate()
            self._in_message_queue.clear()
            self._socket.start_read(self._on_read)
            self._flush_write_queue()

    def _on_read(self, data: bytes):
        read_callback = None
        has_new_messages = False
        with self._lock:
            self._read_buff.write(data)

            self._read_buff.seek(0, io.SEEK_SET)
            data = self._read_buff.getvalue()
            new_pos, messages = self._parse_messages(data)
            self._in_message_queue.extend(messages)

            data = data[new_pos:]
            self._read_buff.write(data)
            self._read_buff.truncate(len(data))

            if len(messages) > 0:
                has_new_messages = True
                read_callback = self._on_next_read
                self._on_next_read = None


        if has_new_messages:
            logger.info('[SIP] [TCP-C] Notifying new messages')
            self._read_event.set()

            if read_callback is not None:
                read_callback()


    def _flush_write_queue(self):
        while len(self._out_message_queue) > 0:
            message = self._out_message_queue.popleft()
            self._socket.write(message.compose().encode('utf-8'))

    @staticmethod
    def _parse_messages(data: bytes) -> Tuple[int, List[Message]]:
        data = data.decode('utf-8')

        messages = []
        start = 0

        while start < len(data):
            end_of_headers = data.find('\r\n\r\n', start)
            if end_of_headers < 0:
                break

            message = parse(data, start)
            messages.append(message)

            start = end_of_headers + len('\r\n\r\n') + len(message.body)

        return start, messages


class AutoConnectSipTcpSocket(SipTcpSocket):

    def __init__(self, local_address: InetAddress, remote_address: InetAddress, selector: Selector):
        super().__init__()
        self._local_address = local_address
        self._remote_address = remote_address
        self._selector = selector

    def send(self, message: Message):
        with self._lock:
            if self._socket is None:
                self._start_open_and_connect()

        super().send(message)

    def await_message(self, timeout: float) -> Optional[Message]:
        with self._lock:
            if self._socket is None:
                self._start_open_and_connect()

        return super().await_message(timeout=timeout)

    def _start_open_and_connect(self):
        logger.info('[SIP] [TCP-C] Opening new socket (bind %s) and connecting (remote %s)', self._local_address, self._remote_address)

        skt = TcpSocket()
        skt.bind(self._local_address.ip, self._local_address.port)
        skt.register_to(self._selector)

        self._attach_socket(skt)

        skt.connect(self._remote_address.ip, self._remote_address.port, self._on_connect)

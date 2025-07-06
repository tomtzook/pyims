import io
import logging
import threading
from abc import ABC, abstractmethod
from collections import deque
from typing import Optional, Callable, Tuple, List

from .message import Message
from .parser import parse
from ..nio.selector import Selector, SelectorThread
from ..nio.sockets import InetAddress, TcpSocket, UdpSocket

logger = logging.getLogger('pyims.sip.transport')


class Transaction(ABC):

    def __init__(self,
                 on_new_messages: Optional[Callable[[], None]] = None,
                 on_error: Optional[Callable[[Exception], None]] = None):
        self._lock = threading.RLock()
        self._read_event = threading.Event()
        self._read_buff = io.BytesIO()
        self._in_message_queue: deque[Message] = deque()
        self._on_new_messages_callback = on_new_messages
        self._on_error_callback = on_error
        self._errored = False

    @abstractmethod
    def send(self, msg: Message):
        pass

    def await_message(self, timeout: float = 5) -> Optional[Message]:
        with self._lock:
            self._throw_if_errored()

            if len(self._in_message_queue) > 0:
                return self._in_message_queue.popleft()

        if self._read_event.wait(timeout):
            self._read_event.clear()

            with self._lock:
                self._throw_if_errored()
                return self._in_message_queue.popleft()
        else:
            raise TimeoutError()

    @abstractmethod
    def close(self):
        pass

    def _on_read(self, data: Optional[bytes]):
        if data is None:
            # TODO: END OF STREAM
            return

        read_callback = None
        has_new_messages = False
        with self._lock:
            if self._errored:
                return

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
                read_callback = self._on_new_messages_callback

        if has_new_messages:
            logger.info('[SIP] Notifying new messages')
            self._read_event.set()

            if read_callback is not None:
                read_callback()

    def _on_error(self, ex: Exception):
        callback = None
        with self._lock:
            self._errored = True
            callback = self._on_error_callback

        self._read_event.set()

        if callback:
            callback(ex)

    def _throw_if_errored(self):
        if self._errored:
            raise EnvironmentError('transaction failure')

    @staticmethod
    def _parse_messages(data: bytes) -> Tuple[int, List[Message]]:
        data = data.decode('utf-8')

        messages = []
        start = 0

        while start < len(data):
            end_of_headers = data.find('\r\n\r\n', start)
            if end_of_headers < 0:
                break

            message, size = parse(data, start)
            messages.append(message)

            start += size

        return start, messages


class Transport(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def selector(self) -> Selector:
        pass

    @abstractmethod
    def open(self,
             local_address: InetAddress,
             remote_address: InetAddress,
             on_new_messages: Callable[[], None],
             on_error: Callable[[Exception], None]) -> Transaction:
        pass

    @abstractmethod
    def close(self):
        pass


class TcpTransaction(Transaction):

    def __init__(self,
                 selector: Selector,
                 local_address: InetAddress,
                 remote_address: InetAddress,
                 on_new_messages: Callable[[], None],
                 on_error: Callable[[Exception], None]):
        super().__init__(on_new_messages, on_error)
        self._socket: Optional[TcpSocket] = None
        self._is_connected: bool = False
        self._out_message_queue: deque[Message] = deque()

        self._start_open_and_connect(selector, local_address, remote_address)

    def send(self, message: Message):
        with self._lock:
            self._throw_if_errored()

            logger.debug('[SIP] [TCP-C] User sending new message %s', message.compose())

            if self._socket is None:
                return

            if not self._is_connected:
                self._out_message_queue.append(message)
            else:
                self._socket.write(message.compose().encode("utf-8"))

    def close(self):
        with self._lock:
            if self._socket is not None:
                self._socket.close()
                self._socket = None

    def _start_open_and_connect(self,
                                selector: Selector,
                                local_address: InetAddress,
                                remote_address: InetAddress):
        logger.info('[SIP] [TCP-C] Opening new socket (bind %s) and connecting (remote %s)', local_address,
                    remote_address)

        skt = TcpSocket(error_callback=self._on_error)
        skt.bind(local_address)
        skt.register_to(selector)
        self._socket = skt

        skt.connect(remote_address, self._on_connect)

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

    def _flush_write_queue(self):
        while len(self._out_message_queue) > 0:
            message = self._out_message_queue.popleft()
            self._socket.write(message.compose().encode('utf-8'))


class TcpTransport(Transport):

    def __init__(self, ):
        super().__init__()
        self._selector_thread = SelectorThread()

    @property
    def name(self) -> str:
        return 'TCP'

    @property
    def selector(self) -> Selector:
        return self._selector_thread.selector

    def open(self,
             local_address: InetAddress,
             remote_address: InetAddress,
             on_new_messages: Callable[[], None],
             on_error: Callable[[Exception], None]) -> Transaction:
        return TcpTransaction(self._selector_thread.selector, local_address, remote_address, on_new_messages, on_error)

    def close(self):
        del self._selector_thread


class UdpTransaction(Transaction):

    def __init__(self, selector: Selector,
                 local_address: InetAddress,
                 remote_address: InetAddress,
                 on_new_messages: Callable[[], None],
                 on_error: Callable[[Exception], None]):
        super().__init__(on_new_messages, on_error)
        self._socket = UdpSocket(error_callback=self._on_error)
        self._remote_address = remote_address

        self._socket.bind(local_address)
        self._socket.register_to(selector)
        self._socket.start_read(self._on_read_custom)

    def send(self, message: Message):
        with self._lock:
            self._throw_if_errored()

            logger.debug('[SIP] [UDP] User sending new message %s', message.compose())

            if self._socket is None:
                return

            self._socket.write((self._remote_address, message.compose().encode("utf-8")))

    def close(self):
        with self._lock:
            if self._socket is not None:
                self._socket.close()
                self._socket = None

    def _on_read_custom(self, data: Optional[Tuple[InetAddress, bytes]]):
        self._on_read(data[1] if data is not None else None)


class UdpTransport(Transport):

    def __init__(self, ):
        super().__init__()
        self._selector_thread = SelectorThread()

    @property
    def name(self) -> str:
        return 'UDP'

    @property
    def selector(self) -> Selector:
        return self._selector_thread.selector

    def open(self,
             local_address: InetAddress,
             remote_address: InetAddress,
             on_new_messages: Callable[[], None],
             on_error: Callable[[Exception], None]) -> Transaction:
        return UdpTransaction(self._selector_thread.selector, local_address, remote_address, on_new_messages, on_error)

    def close(self):
        del self._selector_thread

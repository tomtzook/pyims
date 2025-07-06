import select
import socket
import threading
import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Tuple
from collections import deque

from pyims.nio.inet import InetAddress

logger = logging.getLogger('pyims.nio.selector')


class SelectorRegistration(ABC):

    def __init__(self, resource):
        self._resource = resource
        self._lock = None
        self._readable = False
        self._writable = False
        self._on_config_change = None

    @property
    def reg_id(self):
        return self._resource.fileno()

    @property
    def resource(self):
        return self._resource

    @property
    def readable(self) -> bool:
        with self._lock:
            return self._readable

    @property
    def writable(self) -> bool:
        with self._lock:
            return self._writable

    def mark_readable(self, enabled: bool, notify: bool = False):
        assert self._lock is not None, "not attached to selector"

        with self._lock:
            if self._readable == enabled:
                return

            logger.debug('[Reg %d] Marking as readable (notify: %d)', self.reg_id, notify)
            self._readable = enabled

            if notify and self._on_config_change is not None:
                self._on_config_change()

    def mark_writable(self, enabled: bool, notify: bool = False):
        assert self._lock is not None, "not attached to selector"

        with self._lock:
            if self._writable == enabled:
                return

            logger.debug('[Reg %d] Marking as writable (notify: %d)', self.reg_id, notify)
            self._writable = enabled

            if notify and self._on_config_change is not None:
                self._on_config_change()

    def attach(self, on_config_change: Callable[[], None], lock: threading.RLock):
        self._lock = lock
        self._on_config_change = on_config_change

    @abstractmethod
    def on_read(self):
        pass

    @abstractmethod
    def on_write(self):
        pass

    @abstractmethod
    def on_closed(self):
        pass

    @abstractmethod
    def on_except(self):
        pass


class TcpRegistration(SelectorRegistration):

    def __init__(self, resource: socket.socket,
                 read_callback: Callable[[bytes], None],
                 connect_callback: Callable[[], None],
                 error_callback: Callable[[Exception], None],
                 closed_callback: Callable[[], None],
                 already_connected: bool = False):
        super().__init__(resource)

        self._read_callback = read_callback
        self._connect_callback = connect_callback
        self._error_callback = error_callback
        self._closed_callback = closed_callback

        self._send_queue: deque[bytes] = deque()
        self._connecting: bool = False
        self._connected: bool = False

        if already_connected:
            self._connected = True

    def mark_state_connecting(self):
        with self._lock:
            logger.info('[Reg %d] Marked Connecting', self.reg_id)
            self._connecting = True
            self.mark_writable(True, notify=True)

    def start_read(self):
        logger.debug('[Reg %d] Starting Read', self.reg_id)
        self.mark_readable(True, notify=True)

    def enqueue_send(self, data: bytes):
        with self._lock:
            logger.debug('[Reg %d] Enqueue new Write (len %d)', self.reg_id, len(data))
            self._send_queue.append(data)
            self.mark_writable(True, notify=True)

    def on_read(self):
        logger.debug('[Reg %d] On Read', self.reg_id)
        if not self._connected:
            return

        try:
            data = self.resource.recv(4096)
            if data is None or len(data) == 0:
                # eof
                logger.info('[Reg %d] Read EOF', self.reg_id)
                self.on_closed()
            else:
                logger.info('[Reg %d] Read new data (len %d)', self.reg_id, len(data))
                self._read_callback(data)
        except Exception as e:
            self._on_error(e)

    def on_write(self):
        logger.debug('[Reg %d] On Write', self.reg_id)
        if self._connected:
            # connected, so we are wanting to write
            if len(self._send_queue) > 0:
                self._do_write()
        elif self._connecting:
            # unconnected, so we are wanting to connect
            self._finalize_connect()

    def on_closed(self):
        self._closed_callback()

    def on_except(self):
        logger.debug('[Reg %d] On Except', self.reg_id)
        self._on_error(None)  # TODO: GET ERROR

    def _do_write(self):
        logger.info('[Reg %d] Flushing from Write Queue', self.reg_id)

        write_count = 10  # to not over saturate on write
        while len(self._send_queue) > 0 and write_count > 0:
            write_count -= 1

            data = self._send_queue.popleft()
            try:
                logger.debug('[Reg %d] Writing new data (len %d) to socket', self.reg_id, len(data))
                self.resource.send(data)
            except OSError as e:
                if e.errno in (11, 115, 15):
                    # operation not finished, re-add the data to send again
                    self._send_queue.appendleft(data)
                    break
                else:
                    # errored
                    self._on_error(e)
                    break

        if len(self._send_queue) < 1:
            self.mark_writable(False)

    def _finalize_connect(self):
        logger.info('[Reg %d] Finalizing Connection', self.reg_id)

        self._connecting = False
        self._connected = True

        try:
            self.mark_writable(False)
            self._connect_callback()
        except Exception as e:
            self._on_error(e)

    def _on_error(self, e: Exception):
        logger.debug('[Reg %d] On Error', self.reg_id)
        try:
            self._error_callback(e)
        except:
            pass


class TcpServerRegistration(SelectorRegistration):

    def __init__(self, resource: socket.socket,
                 connect_callback: Callable[[], None],
                 error_callback: Callable[[Exception], None]):
        super().__init__(resource)

        self._connect_callback = connect_callback
        self._error_callback = error_callback

    def start_listening(self):
        logger.info('[Reg %d] Starting to Listen', self.reg_id)
        self.mark_readable(True, notify=True)

    def on_read(self):
        logger.debug('[Reg %d] On Read', self.reg_id)
        try:
            logger.info('[Reg %d] New Connection Arrived', self.reg_id)
            self._connect_callback()
        except Exception as e:
            self._on_error(e)

    def on_write(self):
        pass

    def on_closed(self):
        pass

    def on_except(self):
        logger.debug('[Reg %d] On Except', self.reg_id)
        self._on_error(None)

    def _on_error(self, e: Exception):
        logger.debug('[Reg %d] On Error', self.reg_id)
        try:
            self._error_callback(e)
        except:
            pass


class UdpRegistration(SelectorRegistration):

    def __init__(self, resource: socket.socket,
                 read_callback: Callable[[InetAddress, bytes], None],
                 error_callback: Callable[[Exception], None],
                 closed_callback: Callable[[], None]):
        super().__init__(resource)

        self._read_callback = read_callback
        self._error_callback = error_callback
        self._closed_callback = closed_callback

        self._send_queue: deque[Tuple[InetAddress, bytes]] = deque()

    def start_read(self):
        logger.debug('[Reg %d] Starting Read', self.reg_id)
        self.mark_readable(True, notify=True)

    def enqueue_send(self, dest: InetAddress, data: bytes):
        with self._lock:
            logger.debug('[Reg %d] Enqueue new Write (len %d)', self.reg_id, len(data))
            self._send_queue.append((dest, data))
            self.mark_writable(True, notify=True)

    def on_read(self):
        logger.debug('[Reg %d] On Read', self.reg_id)

        try:
            data, sender = self.resource.recvfrom(4096)
            if data is None or len(data) < 1:
                # eof
                self.on_closed()
            else:
                logger.info('[Reg %d] Read new data (len %d)', self.reg_id, len(data))
                self._read_callback(InetAddress(*sender), data)
        except Exception as e:
            self._on_error(e)

    def on_write(self):
        logger.debug('[Reg %d] On Write', self.reg_id)
        if len(self._send_queue) > 0:
            self._do_write()

    def on_closed(self):
        self._closed_callback()

    def on_except(self):
        logger.debug('[Reg %d] On Except', self.reg_id)
        self._on_error(None)

    def _do_write(self):
        logger.info('[Reg %d] Flushing from Write Queue', self.reg_id)

        write_count = 10  # to not over saturate on write
        while len(self._send_queue) > 0 and write_count > 0:
            write_count -= 1

            dest, data = self._send_queue.popleft()
            try:
                logger.debug('[Reg %d] Writing new data (len %d) to socket', self.reg_id, len(data))
                self.resource.sendto(data, (dest.ip, dest.port))
            except OSError as e:
                if e.errno in (11, 115, 15):
                    # operation not finished, re-add the data to send again
                    self._send_queue.appendleft((dest, data))
                    break
                else:
                    # errored
                    self._on_error(e)
                    break

        if len(self._send_queue) < 1:
            self.mark_writable(False)

    def _on_error(self, e: Exception):
        logger.debug('[Reg %d] On Error', self.reg_id)
        try:
            self._error_callback(e)
        except:
            pass


class Selector(object):

    def __init__(self):
        self._registered: Dict[int, SelectorRegistration] = dict()

        self._readable_lst: List = []
        self._writable_lst: List = []
        self._exception_lst: List = []
        self._lock = threading.RLock()
        self._eventfd = os.eventfd(0, os.EFD_NONBLOCK)
        self._stop_run = False

    def register(self, registration: SelectorRegistration):
        with self._lock:
            skt_id = registration.reg_id
            logger.debug('[Selector] Registering New %d', skt_id)
            self._registered[skt_id] = registration

            registration.attach(self._on_reg_config_changed, self._lock)
            self._signal_run()

    def disable(self):
        with self._lock:
            self._stop_run = True
            self._signal_run()

    def run(self, timeout: float):
        try:
            with self._lock:
                if self._stop_run:
                    return

                self._recompute_select_lists()

            logger.debug('[Selector] Entering select (r=%d, w=%d, e=%d)', len(self._readable_lst),
                         len(self._writable_lst), len(self._exception_lst))
            readable, writable, exceptional = select.select(self._readable_lst, self._writable_lst, self._exception_lst,
                                                            timeout)
            logger.debug('[Selector] Exiting select (r=%d, w=%d, e=%d)', len(readable), len(writable), len(exceptional))

            with self._lock:
                if self._stop_run:
                    return

                for res_id in exceptional:
                    if res_id in self._registered:
                        self._registered[res_id].on_except()

                for res_id in readable:
                    if res_id in self._registered:
                        self._registered[res_id].on_read()
                    elif res_id == self._eventfd:
                        logger.debug('[Selector] Run Event Signalled')
                        os.eventfd_read(self._eventfd)

                for res_id in writable:
                    if res_id in self._registered:
                        self._registered[res_id].on_write()
        except:
            logger.exception('[Selector] Error in select run')
            time.sleep(timeout)  # wait and try again

    def run_forever(self, timeout: float):
        while not self._stop_run:
            self.run(timeout)

    def _recompute_select_lists(self):
        self._readable_lst.clear()
        self._writable_lst.clear()
        self._exception_lst.clear()

        self._readable_lst.append(self._eventfd)

        to_remove = []

        for reg_id, reg in self._registered.items():
            if reg.resource.fileno() < 0:
                to_remove.append(reg_id)
                continue

            if reg.readable:
                self._readable_lst.append(reg.resource.fileno())
            if reg.writable:
                self._writable_lst.append(reg.resource.fileno())

            # everyone in exception
            self._exception_lst.append(reg.resource.fileno())

        for reg_id in to_remove:
            logger.info('[Selector] Removing registration %d because fd closed', reg_id)
            reg = self._registered.pop(reg_id)
            if reg is not None:
                reg.on_closed()

    def _on_reg_config_changed(self):
        with self._lock:
            self._signal_run()

    def _signal_run(self):
        logger.debug('[Selector] Signalling Run')
        os.eventfd_write(self._eventfd, 1)


class SelectorThread(object):

    def __init__(self):
        self._selector = Selector()
        self._thread = threading.Thread(target=self._selector.run_forever, args=(100,), daemon=True)
        self._thread.start()

    @property
    def selector(self) -> Selector:
        return self._selector

    def __del__(self):
        self._selector.disable()
        self._thread.join()

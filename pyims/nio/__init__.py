from typing import Optional

from .inet import InetAddress
from .selector import Selector, SelectorThread
from .sockets import TcpSocket, TcpServerSocket, UdpSocket


_SELECTOR_THREAD: Optional[SelectorThread] = None


def get_default_selector() -> Selector:
    global _SELECTOR_THREAD
    if _SELECTOR_THREAD is None:
        _SELECTOR_THREAD = SelectorThread()

    return _SELECTOR_THREAD.selector


def create_tcp_socket(
        select: Optional[Selector] = None,
        bind_addr: Optional[InetAddress] = None) -> TcpSocket:
    select = select if select is not None else get_default_selector()
    skt = TcpSocket()
    if bind_addr is not None:
        skt.bind(bind_addr)
    skt.register_to(select)
    return skt


def create_udp_socket(
        select: Optional[Selector] = None,
        bind_addr: Optional[InetAddress] = None) -> UdpSocket:
    select = select if select is not None else get_default_selector()
    skt = UdpSocket()
    if bind_addr is not None:
        skt.bind(bind_addr)
    skt.register_to(select)
    return skt

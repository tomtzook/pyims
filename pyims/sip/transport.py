from typing import Optional, Callable

from pyims.nio.selector import Selector, SelectorThread
from pyims.nio.sockets import InetAddress, TcpSocket, TcpServerSocket
from pyims.sip.message import RequestMessage, ResponseMessage
from pyims.sip.sockets import AutoConnectSipTcpSocket, SipTcpSocket


class TcpTransaction(object):

    def __init__(self, selector: Selector, local_address: InetAddress, remote_address: InetAddress):
        self._socket = AutoConnectSipTcpSocket(local_address, remote_address, selector)

    def request(self, msg: RequestMessage, timeout: float = 5) -> ResponseMessage:
        self._socket.send(msg)
        return self.await_response(timeout=timeout)

    def respond(self, msg: ResponseMessage):
        self._socket.send(msg)

    def await_response(self, timeout: float = 5) -> ResponseMessage:
        response = self._socket.await_message(timeout)
        if response is None:
            raise TimeoutError()

        assert isinstance(response, ResponseMessage), 'message is not response'
        return response


class TcpTransport(object):

    def __init__(self, ):
        super().__init__()
        self._selector_thread = SelectorThread()

        self._server_socket: Optional[TcpServerSocket] = None

    def start_transaction(self, local_address: InetAddress, remote_address: InetAddress):
        return TcpTransaction(self._selector_thread.selector, local_address, remote_address)

    def start_listen(self, local_address: InetAddress, on_request: Callable[[SipTcpSocket, RequestMessage], None]):
        if self._server_socket is not None:
            self._server_socket.close()
            self._server_socket = None

        def _on_next_read(skt: SipTcpSocket):
            request = skt.await_message(0.1)
            assert isinstance(request, RequestMessage), "message is not request"
            on_request(skt, request)

        def _on_new_connect(client: TcpSocket):
            client.register_to(self._selector_thread.selector)

            sip_skt = SipTcpSocket()
            # noinspection PyProtectedMember
            sip_skt._attach_socket(client, connected=True, on_next_read=lambda: _on_next_read(sip_skt))
        
        self._server_socket = TcpServerSocket()
        self._server_socket.register_to(self._selector_thread.selector)
        self._server_socket.bind(local_address.ip, local_address.port)
        self._server_socket.listen(10, _on_new_connect)

import logging
import random
from contextlib import contextmanager
from typing import List, Optional, Union, Tuple, Callable, Any

from .bodies import wrap_body
from .headers import Header, CSeq, Via, Expires, MaxForwards, SipHeader, From, CallID, To
from .message import RequestMessage, ResponseMessage
from .sip_types import Method, Version, StatusCode, MessageType, Status, User
from .transport import Transport, Transaction
from ..nio.inet import InetAddress

logger = logging.getLogger('pyims.sip.session')


class SipSession(object):

    def __init__(self,
                 transport: Transport,
                 local_address: InetAddress,
                 server_endpoint: InetAddress,
                 user: User,
                 default_headers: Optional[List[SipHeader]] = None):
        self._transport = transport
        self._local_address = local_address
        self._server_endpoint = server_endpoint
        self._username = user.username
        self._server_host = user.host
        self._default_headers = default_headers if default_headers is not None else list()
        self._transaction: Optional[Transaction] = None
        self._in_transaction: bool = False
        self._listeners = []

    def listen(self, method_or_methods: Union[Method, List[Method]], callback: Callable[[Transaction, RequestMessage], None]):
        methods = method_or_methods if isinstance(method_or_methods, list) else [method_or_methods]
        self._listeners.append((methods, callback))

    def run_transaction(self, request: RequestMessage, on_response: Callable[[Transaction, ResponseMessage], Tuple[bool, Any]], timeout: int = 5) -> Optional[Any]:
        with self._request(request) as transaction:
            while True:
                response = transaction.await_message(timeout=timeout)
                assert isinstance(response, ResponseMessage)

                done, data = on_response(transaction, response)
                if done:
                    return data

    def create_request(
            self,
            method: Method,
            to: Optional[User] = None,
            seq_num: int = 1,
            target_uri: Optional[str] = None,
            additional_headers: List[Header] = None,
            body: Optional[Any] = None,
            content_type: Optional[str] = None,
            branch: Optional[str] = None,
            max_forwards: int = 70,
            expires: int = 1800,
            tag: Optional[str] = None,
            call_id: Optional[str] = None,
            include_self_in_target_uri: bool = False,
            target_uri_to_user: bool = False
    ) -> RequestMessage:
        if target_uri is None:
            if target_uri_to_user:
                assert to is not None
                target_uri = f"sip:{to.username}@{to.host}"
            elif include_self_in_target_uri:
                target_uri = f"sip:{self._username}@{self._server_host}:{self._local_address.ip}"
            else:
                target_uri = f"sip:{self._server_host}"
        if additional_headers is None:
            additional_headers = list()

        request = RequestMessage(Version.VERSION_2, method, target_uri, additional_headers, wrap_body(body, content_type))
        request.add_header(CSeq(method, seq_num), override=True)
        request.add_header(MaxForwards(max_forwards), override=True)
        request.add_header(Expires(expires), override=True)

        tag = tag or self.generate_tag()
        from_uri = f"sip:{self._username}@{self._server_host}"
        request.add_header(From(uri=from_uri, tag=tag), override=True)

        call_id = call_id or self.generate_callid()
        request.add_header(CallID(f"{call_id}@{self._local_address.ip}"), override=True)

        branch = branch or self.generate_branch(method)
        request.add_header(Via(Version.VERSION_2, self._transport.name, self._local_address, branch=branch), override=False)

        to_uri = f"sip:{to.username}@{to.host}" if to is not None else from_uri
        request.add_header(To(uri=to_uri), override=True)

        for header in self._default_headers:
            request.add_header(header)

        return request

    def create_response(
            self,
            status: Union[StatusCode, Status],
            original_request: RequestMessage,
            additional_headers: List[Header] = None,
            body: Optional[Any] = None,
            content_type: Optional[str] = None,
            max_forwards: int = 70,
            expires: int = 1800
    ) -> ResponseMessage:
        if additional_headers is None:
            additional_headers = list()

        response = ResponseMessage(Version.VERSION_2, status, additional_headers, wrap_body(body, content_type))
        response.add_header(original_request.header(From))
        response.add_header(original_request.header(To))
        response.add_header(original_request.header(CallID))
        response.add_header(CSeq(original_request.method, original_request.header(CSeq).sequence), override=True)
        response.add_header(MaxForwards(max_forwards), override=True)
        response.add_header(Expires(expires), override=True)

        for header in self._default_headers:
            response.add_header(header)

        return response

    def close(self):
        if self._transaction is not None:
            self._transport.close()

        self._transaction = None
        self._in_transaction = False

    @contextmanager
    def _request(self, request: RequestMessage):
        logger.info('Sending request: \n%s', request.compose())

        if self._transaction is None:
            self._transaction = self._transport.open(
                self._local_address,
                self._server_endpoint,
                self._on_messages,
                self._on_error
            )

        self._transaction.send(request)
        self._in_transaction = True
        yield self._transaction
        self._in_transaction = False

    def _respond(self, response: ResponseMessage):
        logger.info('Sending response: \n', response.compose())

        if self._transaction is None:
            self._transaction = self._transport.open(
                self._local_address,
                self._server_endpoint,
                self._on_messages,
                self._on_error
            )

        self._transaction.send(response)

    def _on_messages(self):
        if self._transaction is None or self._in_transaction:
            return

        logger.debug('New messages received')
        msg = self._transaction.await_message()

        if msg.type == MessageType.RESPONSE:
            logger.warning('Got response message to async handler')
            return

        assert isinstance(msg, RequestMessage)
        for wanted_methods, callback in self._listeners:
            if msg.method in wanted_methods:
                callback(self._transaction, msg)

    def _on_error(self, ex: Exception):
        logger.exception('Error receives in session, closing', exc_info=ex)
        self.close()

    @staticmethod
    def generate_callid() -> str:
        return f"call-aa11-{random.randint(100, 5000)}"

    @staticmethod
    def generate_tag() -> str:
        return f"aq111aw-{random.randint(100, 5000)}"

    @staticmethod
    def generate_branch(method: Optional[Method] = None) -> str:
        return f"pyimsbranch-{random.randint(100, 5000)}-{method.name.lower() if method else 'any'}"

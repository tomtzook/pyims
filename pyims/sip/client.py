import logging
from contextlib import contextmanager
from typing import List, Optional

from ..nio.inet import InetAddress
from .headers import Header, CSeq, Via, CallID, ContentLength, Expires, MaxForwards, CustomHeader, From, To, \
    Contact, Authorization, WWWAuthenticate
from .message import RequestMessage
from .sip_types import Method, Version, StatusCode, AuthenticationScheme, AuthenticationAlgorithm
from .sockets import SipSocket
from .transport import Transport
from .auth import Account, create_auth_header


logger = logging.getLogger('pyims.sip.client')


class Client(object):

    def __init__(self,
                 transport: Transport,
                 local_address: InetAddress,
                 server_endpoint: InetAddress,
                 account: Account):
        self._transport = transport
        self._local_address = local_address
        self._server_endpoint = server_endpoint
        self._account = account
        self._server_host = self._generate_ims_host()

    def register(self):
        logger.info('Client starting registration with network')

        self._transport.start_listen(self._local_address, self._on_request)

        with self._request(Method.REGISTER, '', headers=self._create_headers_for_register()) as transaction:
            while True:
                response = transaction.await_response(timeout=5)
                print(response)

                if response.status.code == StatusCode.TRYING:
                    print('Trying')
                    continue
                elif response.status.code == StatusCode.OK:
                    print('Ok')
                    break
                elif response.status.code == StatusCode.UNAUTHORIZED:
                    assert 'WWW-Authenticate' in response.headers
                    transaction.send(self._create_request(Method.REGISTER, '',
                                                          headers=self._create_headers_for_register(response.headers['WWW-Authenticate'])))
                    continue
                else:
                    raise RuntimeError(f"Register failed: {response.status}")

    @contextmanager
    def _request(self, method: Method, body: str,
                seq_num: int = 1,
                headers: List[Header] = None):
        if headers is None:
            headers = list()

        logger.info('Starting transaction and sending request')

        transaction = self._transport.start_transaction(
            InetAddress(self._local_address.ip, 50601), self._server_endpoint)
        try:
           request = self._create_request(method, body, seq_num, headers)
           print(request.compose())

           transaction.send(request)
           yield transaction
        finally:
            transaction.close()

    def close(self):
        self._transport.close()

    def _create_headers_for_register(self, authenticate_header: Optional[WWWAuthenticate] = None):
        return [
            From(uri=f"sip:{self._account.imsi}@{self._server_host}", tag='4130282085'),
            To(uri=f"sip:{self._account.imsi}@{self._server_host}"),
            CallID(f"1-119985@{self._local_address.ip}"),
            CustomHeader('Supported', 'path'),
            CustomHeader('P-Access-Network-Info', '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'),
            CustomHeader('Allow', ','.join([method.value for method in list(Method)])),
            Via(Version.VERSION_2, 'TCP', self._local_address, branch='z9hG4bK3987742761'),
            Contact(self._local_address),
            create_auth_header(Method.REGISTER, self._account, self._server_host, authenticate_header)
        ]

    def _create_request(self, method: Method,
                        body: str,
                        seq_num: int = 1,
                        headers: List[Header] = None):
        request = RequestMessage(Version.VERSION_2, method, f"sip:{self._server_host}", headers, body)
        request.add_header(CSeq(method, seq_num), override=False)
        request.add_header(MaxForwards(70), override=False)
        request.add_header(Expires(1800), override=False)
        request.add_header(ContentLength(len(body)), override=True)

        return request

    def _on_request(self, client: SipSocket, request: RequestMessage):
        pass

    def _generate_ims_host(self):
        return f"ims.mnc{self._account.mnc}.mcc{self._account.mcc}.3gppnetwork.org"

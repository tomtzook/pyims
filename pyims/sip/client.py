import logging
import random
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

        with self._request(self._create_request(
                Method.REGISTER,
                headers=self._create_headers_for_register())) as transaction:
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
                    # we must authorize ourselves
                    assert 'WWW-Authenticate' in response.headers
                    auth_header = response.headers['WWW-Authenticate']
                    assert isinstance(auth_header, WWWAuthenticate)

                    transaction.send(
                        self._create_request(
                            Method.REGISTER,
                            headers=self._create_headers_for_register(auth_header))
                    )
                    continue
                else:
                    raise RuntimeError(f"Register failed: {response.status}")

    def invite(self, invitee: str, subject: str):
        with self._request(self._create_request(
                Method.INVITE,
                target_uri=f"sip:{invitee}",
                headers=self._create_headers_for_invite(invitee, subject))) as transaction:
            while True:
                response = transaction.await_response(timeout=5)
                print(response)

                if response.status.code == StatusCode.TRYING:
                    print('Trying')
                    continue
                elif response.status.code == StatusCode.OK:
                    print('Ok')
                    break
                else:
                    raise RuntimeError(f"Register failed: {response.status}")

    @contextmanager
    def _request(self, request: RequestMessage):
        logger.info('Starting transaction and sending request')

        transaction = self._transport.start_transaction(
            InetAddress(self._local_address.ip, self._generate_port()),
            self._server_endpoint)
        try:
           print(request.compose())

           transaction.send(request)
           yield transaction
        finally:
            transaction.close()

    def close(self):
        self._transport.close()

    def _create_request(self,
                        method: Method,
                        seq_num: int = 1,
                        target_uri: Optional[str] = None,
                        headers: List[Header] = None,
                        body: str = '',
                        content_type: Optional[str] = None):
        if target_uri is None:
            target_uri = f"sip:{self._server_host}"
        if headers is None:
            headers = list()

        request = RequestMessage(Version.VERSION_2, method, target_uri, headers, body)
        request.add_header(CSeq(method, seq_num), override=False)
        request.add_header(MaxForwards(70), override=False)
        request.add_header(Expires(1800), override=False)
        request.add_header(ContentLength(len(body)), override=True)
        request.add_header(Via(Version.VERSION_2, self._transport.name, self._local_address, branch=self._generate_branch(method)))

        if len(body) > 0 and content_type is not None:
            request.add_header(CustomHeader('Content-Type', content_type))

        return request

    def _create_headers_for_register(self, authenticate_header: Optional[WWWAuthenticate] = None):
        return [
            From(
                uri=f"sip:{self._account.imsi}@{self._server_host}",
                tag='1'
            ),
            To(uri=f"sip:{self._account.imsi}@{self._server_host}"),
            CallID(f"1-119985@{self._local_address.ip}"),
            CustomHeader('Supported', 'path'),
            CustomHeader(
                'P-Access-Network-Info',
                '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'
            ),
            CustomHeader(
                'Allow',
                ','.join([method.value for method in list(Method)])
            ),
            Contact(
                self._local_address,
                external_tags={
                    '+sip.instance': '"<urn:gsma:imei:35622410-483840-0>"',
                    'q': '1.0',
                    '+g.3gpp.icsi-ref': '"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"',
                    '+g.3gpp.smsip': None
                }
            ),
            create_auth_header(Method.REGISTER, self._account, self._server_host, authenticate_header)
        ]

    def _create_headers_for_invite(self, invitee: str, subject: str):
        return [
            From(
                uri=f"sip:{self._account.imsi}@{self._server_host}",
                tag='1'
            ),
            To(uri=f"sip:{invitee}"),
            CallID(f"1-119985@{self._local_address.ip}"),
            CustomHeader('Supported', 'path'),
            CustomHeader(
                'P-Access-Network-Info',
                '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'
            ),
            CustomHeader('Subject', subject),
            Contact(
                self._local_address,
                external_tags={
                    '+sip.instance': '"<urn:gsma:imei:35622410-483840-0>"',
                    'q': '1.0',
                    '+g.3gpp.icsi-ref': '"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"',
                    '+g.3gpp.smsip': None
                }
            )
        ]

    def _on_request(self, client: SipSocket, request: RequestMessage):
        print('ON REQUEST')
        print(request.compose())
        client.close()

    def _generate_branch(self, method: Method) -> str:
        return f"pyimsbranch-{random.randint(100, 5000)}-{method.name.lower()}"

    def _generate_ims_host(self) -> str:
        return f"ims.mnc{self._account.mnc:03d}.mcc{self._account.mcc:03d}.3gppnetwork.org"

    def _generate_port(self) -> int:
        return random.randint(1000, 5000)

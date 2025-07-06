import logging
import random
from contextlib import contextmanager
from typing import List, Optional, Union, Tuple, Callable, Any, Dict

from .auth import Account, create_auth_header
from .bodies import wrap_body
from .call import CallSession, CallInformation, RtpCallSession, SessionNode
from .headers import Header, CSeq, Via, CallID, Expires, MaxForwards, CustomHeader, From, To, \
    Contact, WWWAuthenticate, RecordRoute
from .message import RequestMessage, ResponseMessage, Message
from .sip_types import Method, Version, StatusCode, MessageType, Status
from .transport import Transport, Transaction
from ..nio.inet import InetAddress
from ..nio.sockets import UdpSocket
from ..sdp import attributes as sdp_attributes
from ..sdp import fields as sdp_fields
from ..sdp.attributes import RtpMap, Fmtp
from ..sdp.message import SdpMessage
from ..sdp.sdp_types import NetworkType, AddressType, MediaType, MediaProtocol, MediaFormat

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
        self._transaction: Optional[Transaction] = None
        self._in_transaction: bool = False
        self._is_registered: bool = False
        self._active_sessions: Dict[int, SessionNode] = dict()
        self._call_callbacks: List[Callable[[CallSession], None]] = []

    def on_new_call(self, callback: Callable[[CallSession], None]):
        self._call_callbacks.append(callback)

    def register(self):
        if self._is_registered:
            return

        logger.info('Client starting registration with network')

        def _on_response(transaction: Transaction, response: ResponseMessage) -> Tuple[bool, None]:
            if response.status.code == StatusCode.TRYING:
                return False, None
            elif response.status.code == StatusCode.OK:
                self._is_registered = True
                return True, None
            elif response.status.code == StatusCode.UNAUTHORIZED:
                # we must authorize ourselves
                auth_header = response.header(WWWAuthenticate)
                assert isinstance(auth_header, WWWAuthenticate)

                transaction.send(self._create_request_register(auth_header))
                return False, None
            else:
                raise RuntimeError(f"Register failed: {response.status}")

        self._do_transaction(self._create_request_register(), _on_response)

    def bye(self):
        if not self._is_registered:
            return

        def _on_response(transaction: Transaction, response: ResponseMessage) -> Tuple[bool, None]:
            if response.status.code == StatusCode.TRYING:
                return False, None
            elif response.status.code == StatusCode.OK:
                self._is_registered = False
                return True, None
            else:
                raise RuntimeError(f"Register failed: {response.status}")

        self._do_transaction(self._create_request_bye(), _on_response)

    def invite(self, invitee: str, subject: str) -> CallSession:
        session_id = self._generate_session_id()
        rtp_port = self._generate_port()
        session_node = SessionNode(session_id)
        self._active_sessions[session_id] = session_node

        local_info = SdpMessage(
            fields=[
                sdp_fields.Version(0),
                sdp_fields.Originator('-', str(session_id), '1', NetworkType.IN, AddressType.IPv4, self._local_address.ip),
                sdp_fields.SessionName('pyims Call'),
                sdp_fields.ConnectionInformation(NetworkType.IN, AddressType.IPv4, self._local_address.ip),
                sdp_fields.MediaDescription(MediaType.AUDIO, rtp_port, MediaProtocol.RTP_AVP, [MediaFormat.PCMU]),
                sdp_fields.BandwidthInformation('AS', 84),
                sdp_fields.BandwidthInformation('TIAS', 64000),
                sdp_fields.TimeDescription(0, 0)
            ],
            attributes=[
                sdp_attributes.RtpMap(MediaFormat.PCMU, 'PCMU', 8000),
                sdp_attributes.RtpMap(MediaFormat.PCMA, 'PCMA', 8000),
                #sdp_attributes.RtpMap(MediaFormat.EVENT, 'telephony-event', 8000),
                sdp_attributes.Fmtp(MediaFormat.PCMU, ['mode-change-capability=2', 'max-red=0']),
                #sdp_attributes.Fmtp(MediaFormat.EVENT, ['0-16']),
                sdp_attributes.Rtcp(rtp_port + 1),
                sdp_attributes.SendRecv(),
                sdp_attributes.Ptime(20)
            ])

        def _on_response(transaction: Transaction, response: ResponseMessage) -> Tuple[bool, Any]:
            if response.status.code == StatusCode.TRYING:
                return False, None
            elif response.status.code == StatusCode.OK:
                remote_info = response.body_as(SdpMessage)
                session = self._create_call_session(local_info, remote_info)
                session_node.attach_session(session)
                return True, session
            else:
                raise RuntimeError(f"Invite failed: {response.status}")

        return self._do_transaction(self._create_request_invite(invitee, subject, local_info), _on_response)

    def close(self):
        if self._transaction is not None:
            if self._is_registered:
                try:
                    self.bye()
                except:
                    # we don't care really if this fails
                    pass

            self._transport.close()

        self._transaction = None
        self._is_registered = False
        self._in_transaction = False

    def _do_transaction(self, request: RequestMessage, on_response: Callable[[Transaction, ResponseMessage], Tuple[bool, Any]], timeout: int = 5) -> Optional[Any]:
        with self._request(request) as transaction:
            while True:
                response = transaction.await_message(timeout=timeout)
                assert isinstance(response, ResponseMessage)
                print(response)

                done, data = on_response(transaction, response)
                if done:
                    return data

    @contextmanager
    def _request(self, request: RequestMessage):
        logger.info('Sending request')
        print(request.compose())

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
        logger.info('Sending response')
        print(response.compose())

        if self._transaction is None:
            self._transaction = self._transport.open(
                self._local_address,
                self._server_endpoint,
                self._on_messages,
                self._on_error
            )

        self._transaction.send(response)

    def _create_request_register(self, authenticate_header: Optional[WWWAuthenticate] = None) -> RequestMessage:
        return self._create_request(
            Method.REGISTER,
            headers=[
                self._generate_from(*self._my_credentials, tag='1'),
                self._generate_to(*self._my_credentials),
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
                self._generate_our_contact(),
                create_auth_header(Method.REGISTER, self._account, self._server_host, authenticate_header)
            ]
        )

    def _create_request_invite(self, invitee: str, subject: str, sdp: SdpMessage) -> RequestMessage:
        return self._create_request(
            Method.INVITE,
            target_uri=f"sip:{invitee}",
            headers=[
                self._generate_from(*self._my_credentials, tag='1'),
                To(uri=f"sip:{invitee}"),
                CallID(f"1-119985@{self._local_address.ip}"),
                CustomHeader('Supported', 'path'),
                CustomHeader(
                    'P-Access-Network-Info',
                    '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'
                ),
                CustomHeader('Subject', subject),
                self._generate_our_contact()
            ],
            body=sdp
        )

    def _create_request_bye(self) -> RequestMessage:
        return self._create_request(
            Method.BYE,
            seq_num=2,
            target_uri=f"sip:{self._account.imsi}@{self._server_host}:{self._local_address.port}",
            headers=[
                self._generate_from(*self._my_credentials, tag='1'),
                self._generate_to(*self._my_credentials),
                CallID(f"1-119985@{self._local_address.ip}"),
                CustomHeader(
                    'P-Access-Network-Info',
                    '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'
                ),
                self._generate_our_contact()
            ]
        )

    def _create_request(self,
                        method: Method,
                        seq_num: int = 1,
                        target_uri: Optional[str] = None,
                        headers: List[Header] = None,
                        body: Optional[Any] = None,
                        content_type: Optional[str] = None) -> RequestMessage:
        if target_uri is None:
            target_uri = f"sip:{self._server_host}"
        if headers is None:
            headers = list()

        request = RequestMessage(Version.VERSION_2, method, target_uri, headers, wrap_body(body, content_type))
        self._added_headers_to_message(request, method, seq_num)

        return request

    def _create_response(self,
                         status: Union[StatusCode, Status],
                         original_request: RequestMessage,
                         headers: List[Header] = None,
                         body: Optional[Any] = None,
                         content_type: Optional[str] = None) -> ResponseMessage:
        if headers is None:
            headers = list()

        response = ResponseMessage(Version.VERSION_2, status, headers, wrap_body(body, content_type))
        self._added_headers_to_message(response,
                                       original_request.method,
                                       original_request.header(CSeq).sequence)

        return response

    def _added_headers_to_message(self, message: Message,
                                  method: Method,
                                  seq_num: int):
        message.add_header(CSeq(method, seq_num), override=False)
        message.add_header(MaxForwards(70), override=False)
        message.add_header(Expires(1800), override=False)
        message.add_header(Via(Version.VERSION_2, self._transport.name, self._local_address, branch=self._generate_branch(method)), override=False)

    def _on_messages(self):
        if self._transaction is None or self._in_transaction:
            return

        logger.debug('New messages received when not in transaction')
        msg = self._transaction.await_message()
        print(msg.compose())

        if msg.type == MessageType.RESPONSE:
            logger.warning('Got response message to async handler')
            return

        assert isinstance(msg, RequestMessage)
        if msg.method == Method.INVITE:
            self._on_invite_request(msg)

    def _on_error(self, ex: Exception):
        self._transaction = None
        self._is_registered = False

    def _on_invite_request(self, request: RequestMessage):
        remote_sdp = request.body_as(SdpMessage)
        print(remote_sdp)

        session_id = self._generate_session_id()
        session_node = SessionNode(session_id)
        self._active_sessions[session_id] = session_node

        local_sdp = self._create_media_response(session_id, remote_sdp)
        print(local_sdp)

        session = self._create_call_session(local_sdp, remote_sdp)
        session_node.attach_session(session)

        self._respond(self._create_response(
            StatusCode.OK,
            request,
            headers=[
                request.header(From),
                request.header(To),
                request.header(CallID),
                request.header(Via),
                request.header(RecordRoute)
            ],
            body=local_sdp
        ))

        for callback in self._call_callbacks:
            callback(session)

        # TODO: HANDLE USER RINGING
        """
        # report that we are trying
        self._respond(self._create_response(
            StatusCode.TRYING,
            headers=[
                msg.header(Via),
                msg.header(From),
                msg.header(To),
                msg.header(CSeq),
                msg.header(CallID)
            ]
        ))
        # todo: start setup
        local_tag = '2'

        # report that we are ringing
        self._respond(self._create_response(
            StatusCode.RINGING,
            headers=[
                msg.header(Via),
                msg.header(From),
                self._generate_to(*self._my_credentials, tag=local_tag),
                msg.header(CSeq),
                msg.header(CallID),
                self._generate_our_contact()
            ]
        ))
        # todo: ring user
        """

    def _create_media_response(self, session_id: int, remote_info: SdpMessage) -> SdpMessage:
        # TODO GENERATE DYNAMICALLY
        port = random.randint(10000, 12000)

        remote_conn_info = remote_info.field(sdp_fields.ConnectionInformation)
        remote_media_info = remote_info.field(sdp_fields.MediaDescription)

        assert remote_conn_info.address_type == AddressType.IPv4
        assert remote_media_info.media_type == MediaType.AUDIO
        assert remote_media_info.protocol == MediaProtocol.RTP_AVP
        assert len(remote_media_info.formats) > 0
        assert MediaFormat.PCMU in remote_media_info.formats
        assert len(remote_info.attribute(sdp_attributes.SendRecv)) > 0

        rtp_map = [rtpmap for rtpmap in remote_info.attribute(sdp_attributes.RtpMap) if rtpmap.media_format == MediaFormat.PCMU][0]
        fmtp = [fmtp for fmtp in remote_info.attribute(sdp_attributes.Fmtp) if fmtp.media_format == MediaFormat.PCMU][0]

        return SdpMessage(fields=[
            sdp_fields.Version(0),
            sdp_fields.Originator('-', str(session_id), '1', NetworkType.IN, AddressType.IPv4, self._local_address.ip),
            sdp_fields.SessionName('pyims Call'),
            sdp_fields.ConnectionInformation(NetworkType.IN, AddressType.IPv4, self._local_address.ip),
            sdp_fields.MediaDescription(MediaType.AUDIO, port, MediaProtocol.RTP_AVP, [MediaFormat.PCMU]),
            sdp_fields.TimeDescription(0, 0)
        ] + remote_info.field(sdp_fields.BandwidthInformation), attributes=[
            rtp_map,
            fmtp,
            sdp_attributes.SendRecv(),
            remote_info.attribute(sdp_attributes.Ptime)[0]
        ])

    def _create_call_session(self, local_info: SdpMessage, remote_info: SdpMessage) -> CallSession:
        info = CallInformation(local_info, remote_info)
        skt = UdpSocket()
        skt.bind(info.local_address)
        skt.register_to(self._transport.selector)

        return RtpCallSession(info, skt)

    def _generate_from(self, username: str, server: str, tag: Optional[str] = None) -> From:
        return From(uri=f"sip:{username}@{server}", tag=tag)

    def _generate_to(self, username: str, server: str, tag: Optional[str] = None) -> To:
        return To(uri=f"sip:{username}@{server}", tag=tag)

    def _generate_our_contact(self) -> Contact:
        return Contact(
            self._local_address,
            internal_tags={
                'transport': self._transport.name
            },
            external_tags={
                '+sip.instance': '"<urn:gsma:imei:35622410-483840-0>"',
                'q': '1.0',
                '+g.3gpp.icsi-ref': '"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"',
                '+g.3gpp.smsip': None
            }
        )

    def _generate_session_id(self) -> int:
        return random.randint(1, 10000)

    def _generate_branch(self, method: Method) -> str:
        return f"pyimsbranch-{random.randint(100, 5000)}-{method.name.lower()}"

    def _generate_ims_host(self) -> str:
        return f"ims.mnc{self._account.mnc:03d}.mcc{self._account.mcc:03d}.3gppnetwork.org"

    def _generate_port(self) -> int:
        return random.randint(1000, 5000)

    @property
    def _my_credentials(self) -> Tuple[str, str]:
        return self._account.imsi, self._server_host

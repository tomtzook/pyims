import logging
from typing import Optional, Tuple, Any

from .auth import Account, Authenticator
from .call import CallHandler, InviteRequest
from .headers import CustomHeader, Contact, WWWAuthenticate, RecordRoute, Via
from .message import RequestMessage, ResponseMessage
from .session import SipSession
from .sip_types import Method, StatusCode, User
from .transport import Transport, Transaction
from ..nio.inet import InetAddress
from ..sdp.message import SdpMessage

logger = logging.getLogger('pyims.sip.client')


class Client(object):

    def __init__(self,
                 session: SipSession,
                 account: Account,
                 authenticator: Authenticator,
                 call_handler: CallHandler):
        self._session = session
        self._account = account
        self._authenticator = authenticator
        self._call_handler = call_handler
        self._is_registered = False

        session.listen(Method.INVITE, self._on_invite_request)

    def register(self):
        if self._is_registered:
            return

        logger.info('Client starting registration with network')

        tag = self._session.generate_tag()
        call_id = self._session.generate_callid()

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

                transaction.send(self._create_request_register(tag, call_id, auth_header))
                return False, None
            else:
                raise RuntimeError(f"Register failed: {response.status}")

        self._session.run_transaction(self._create_request_register(tag, call_id), _on_response)

    def bye(self, remote: User):
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

        self._session.run_transaction(self._create_request_bye(remote), _on_response)

    def invite(self, invitee: User, subject: str, request: InviteRequest) -> InviteRequest:
        tag = self._session.generate_tag()
        branch = self._session.generate_branch(Method.INVITE)
        call_id = self._session.generate_callid()

        local_info = request.compose_to_sdp()

        def _on_response(transaction: Transaction, response: ResponseMessage) -> Tuple[bool, Any]:
            if response.status.code == StatusCode.TRYING:
                return False, None
            elif response.status.code == StatusCode.OK:
                remote_info = response.body_as(SdpMessage)
                remote_request = InviteRequest.parse_from_sdp(remote_info)

                try:
                    success = self._call_handler.on_ack(request, remote_request)
                except Exception as e:
                    success = False
                    logger.exception('Error during call_handler.on_ack', exc_info=e)

                if success:
                    transaction.send(self._create_request_ack(invitee, subject, tag, branch, call_id))
                else:
                    # TODO: RETURN FAILURE
                    transaction.send(self._create_request_ack(invitee, subject, tag, branch, call_id))

                return True, remote_request
            else:
                raise RuntimeError(f"Invite failed: {response.status}")

        return self._session.run_transaction(self._create_request_invite(invitee, subject, tag, branch, call_id, local_info), _on_response)

    def close(self):
        self._session.close()

    def _create_request_register(self, tag: str, call_id: str, authenticate_header: Optional[WWWAuthenticate] = None) -> RequestMessage:
        return self._session.create_request(
            Method.REGISTER,
            additional_headers=[
                CustomHeader('Supported', 'path'),
                self._authenticator.create_auth_header(Method.REGISTER, authenticate_header)
            ],
            call_id=call_id,
            tag=tag
        )

    def _create_request_invite(self, invitee: User, subject: str, tag: str, branch: str, call_id: str, sdp: SdpMessage) -> RequestMessage:
        return self._session.create_request(
            Method.INVITE,
            to=invitee,
            additional_headers=[
                CustomHeader('Supported', 'path'),
                CustomHeader('Subject', subject),
            ],
            body=sdp,
            call_id=call_id,
            branch=branch,
            tag=tag,
            target_uri_to_user=True
        )

    def _create_request_ack(self, invitee: User, subject: str, tag: str, branch: str, call_id: str) -> RequestMessage:
        return self._session.create_request(
            Method.ACK,
            to=invitee,
            additional_headers=[
                CustomHeader('Subject', subject),
            ],
            call_id=call_id,
            branch=branch,
            tag=tag,
            target_uri_to_user=True
        )

    def _create_request_bye(self, remote: User) -> RequestMessage:
        return self._session.create_request(
            Method.BYE,
            to=remote,
            seq_num=2,
            target_uri_to_user=True
        )

    def _on_invite_request(self, transaction: Transaction, request: RequestMessage):
        remote_info = request.body_as(SdpMessage)
        remote_request = InviteRequest.parse_from_sdp(remote_info)

        # TODO: HANDLE USER RINGING
        try:
            response = self._call_handler.on_invite(remote_request)
        except Exception as e:
            response = None
            logger.exception('Error during call_handler.on_invite', exc_info=e)

        if response is not None:
            transaction.send(self._session.create_response(
                StatusCode.OK,
                request,
                additional_headers=[
                    request.header(RecordRoute),
                    request.header(Via)
                ],
                body=response.compose_to_sdp()
            ))
        else:
            transaction.send(self._session.create_response(
                StatusCode.BAD_REQUEST,
                request,
                additional_headers=[
                    request.header(RecordRoute),
                    request.header(Via)
                ]
            ))


def create_client(
        transport: Transport,
        account: Account,
        local_address: InetAddress,
        server_endpoint: InetAddress,
        call_handler: CallHandler
) -> Client:
    server_host = f"ims.mnc{account.mnc:03d}.mcc{account.mcc:03d}.3gppnetwork.org"
    default_headers = [
        Contact(
            local_address,
            internal_tags={
                'transport': transport.name
            },
            external_tags={
                '+sip.instance': '"<urn:gsma:imei:35622410-483840-0>"',
                'q': '1.0',
                '+g.3gpp.icsi-ref': '"urn%3Aurn-7%3A3gpp-service.ims.icsi.mmtel"',
                '+g.3gpp.smsip': None
            }
        ),
        CustomHeader(
            'P-Access-Network-Info',
            '3GPP-E-UTRAN-FDD; utran-cell-id-3gpp=001010001000019B'
        ),
        CustomHeader(
            'Allow',
            ','.join([method.value for method in list(Method)])
        )
    ]
    sip_session = SipSession(transport, local_address, server_endpoint, User(account.imsi, server_host), default_headers)
    auth = Authenticator(account, server_host)
    return Client(sip_session, account, auth, call_handler)

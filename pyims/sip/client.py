from typing import Optional

from pyims.sip.message import Message, RequestMessage, ResponseMessage
from pyims.sip.sip_socket import SipSocket
from pyims.sip.parser import parse
from pyims.sip.transport import Transport


class Client(object):

    def __init__(self, transport: Transport):
        self._transport = transport
        self._skt: Optional[SipSocket] = None

    def request(self, request: RequestMessage) -> ResponseMessage:
        skt = self._get_or_connect_socket()
        skt.write(request.compose().encode('utf-8'))

        # wait for
        data = skt.read()
        return self._parse_message(data)

    def send(self, message: Message):
        skt = self._get_or_connect_socket()
        skt.write(message.compose().encode('utf-8'))

    def close(self):
        if self._skt is not None:
            self._skt.close()
            self._skt = None

    def _get_or_connect_socket(self) -> SipSocket:
        if self._skt is not None:
            return self._skt

        skt = self._transport.connect_socket()
        self._skt = skt
        return skt

    def _parse_message(self, data: bytes) -> ResponseMessage:
        str_data = data.decode('utf-8')
        message = parse(str_data)
        assert isinstance(message, ResponseMessage)

        return message

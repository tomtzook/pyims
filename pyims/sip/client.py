from pyims.sip.message import Message, RequestMessage, ResponseMessage
from pyims.sip.transport import Transport


class Client(object):

    def __init__(self, transport: Transport):
        self._transport = transport

    def request(self, request: RequestMessage) -> ResponseMessage:
        self._transport.send(request)

        responses = self._transport.receive()
        assert len(responses) == 1
        assert isinstance(responses[0], ResponseMessage)
        return responses[0]

    def send(self, message: Message):
        self._transport.send(message)

    def close(self):
        self._transport.close()

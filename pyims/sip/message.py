from abc import ABC, abstractmethod
from typing import List, Dict, Union

from .headers import Header, Request, Response
from .sip_types import Version, MessageType, Method, Status, StatusCode


class Message(ABC):

    def __init__(self, version: Version, headers: List[Header] = None, body: str = ''):
        headers = headers if headers else list()

        self._version = version
        self._headers = {header.name: header for header in headers}
        self._body = body

    @property
    def version(self) -> Version:
        return self._version

    @property
    def headers(self) -> Dict[str, Header]:
        return self._headers

    def add_header(self, header: Header, override: bool = True):
        if header.name in self._headers and not override:
            return
        self._headers[header.name] = header

    @property
    def body(self) -> str:
        return self._body

    @property
    @abstractmethod
    def type(self) -> MessageType:
        pass

    @abstractmethod
    def compose(self) -> str:
        pass

    def __str__(self):
        return self.compose()

    def __repr__(self):
        return self.compose()


class RequestMessage(Message):

    def __init__(self, version: Version, method: Method, server_uri: str, headers: List[Header] = None, body: str = ''):
        super().__init__(version, headers, body)
        self._method = method
        self._server_uri = server_uri

    @property
    def method(self) -> Method:
        return self._method

    @property
    def type(self) -> MessageType:
        return MessageType.REQUEST

    def compose(self) -> str:
        request_header = Request()
        request_header.version = self.version
        request_header.method = self._method
        request_header.uri = self._server_uri

        res = request_header.compose()
        if len(self._headers) > 0:
            res += '\r\n' + '\r\n'.join([f"{header.name}: {header.compose()}" for header in self.headers.values()])
        res += '\r\n\r\n' + self.body

        return res


class ResponseMessage(Message):

    def __init__(self, version: Version, status: Union[StatusCode, Status], headers: List[Header] = None, body: str = ''):
        super().__init__(version, headers, body)
        self._status = status if isinstance(status, Status) else Status(status, status.value[1])

    @property
    def status(self) -> Status:
        return self._status

    @property
    def type(self) -> MessageType:
        return MessageType.RESPONSE

    def compose(self) -> str:
        request_header = Response()
        request_header.version = self.version
        request_header.status = self._status

        res = request_header.compose()
        if len(self._headers) > 0:
            res += '\r\n' + '\r\n'.join([f"{header.name}: {header.compose()}" for header in self.headers.values()])
        res += '\r\n\r\n'

        return res

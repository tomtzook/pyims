from abc import ABC, abstractmethod
from typing import List, Dict, Union, TypeVar, Optional, Generic, AnyStr, Any

from .headers import SipHeader, Request, Response, ContentLength, CustomHeader
from .sip_types import Version, MessageType, Method, Status, StatusCode


T = TypeVar('T')

class Body(ABC, Generic[T]):

    @property
    @abstractmethod
    def value(self) -> T:
        pass

    @property
    @abstractmethod
    def content_type(self) -> Optional[str]:
        pass

    @abstractmethod
    def load_value(self, value: Any) -> bool:
        pass

    @abstractmethod
    def parse_from(self, data: str):
        pass

    @abstractmethod
    def compose(self) -> str:
        pass


class Message(ABC):

    def __init__(self, version: Version,
                 headers: List[SipHeader] = None,
                 body: Optional[Body] = None):
        headers = headers if headers else list()

        self._version = version
        self._headers = {header.name: header for header in headers}
        self._body = body

    @property
    def version(self) -> Version:
        return self._version

    @property
    def headers(self) -> Dict[str, SipHeader]:
        return self._headers

    def header(self, name: Union[str, T]) -> T:
        wanted_name = name if isinstance(name, str) else name.__NAME__
        return self._headers[wanted_name]

    def add_header(self, header: SipHeader, override: bool = True):
        if header.name in self._headers and not override:
            return
        self._headers[header.name] = header

    @property
    def body(self) -> Body:
        return self._body

    def body_as(self, ty: type) -> Any:
        assert self._body is not None

        val = self._body.value
        assert isinstance(val, ty)
        return val

    @property
    @abstractmethod
    def type(self) -> MessageType:
        pass

    def compose(self) -> str:
        headers = dict(self._headers)
        body_str = ''
        if self._body is not None:
            if self._body.content_type is not None:
                header = CustomHeader('Content-Type', self._body.content_type)
                headers[header.name] = header

            body_str = self._body.compose()
            assert body_str is not None

            header = ContentLength(len(body_str))
            headers[header.name] = header
        else:
            header = ContentLength(0)
            headers[header.name] = header

        res = ''
        if len(headers) > 0:
            res += '\r\n'.join([f"{header.name}: {header.compose()}" for header in headers.values()])
        res += '\r\n\r\n' + body_str + '\r\n'

        return res

    def __str__(self):
        return self.compose()

    def __repr__(self):
        return self.compose()


class RequestMessage(Message):

    def __init__(self, version: Version, method: Method, server_uri: str,
                 headers: List[SipHeader] = None,
                 body: Optional[Body] = None):
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

        return request_header.compose() + '\r\n' + super().compose()


class ResponseMessage(Message):

    def __init__(self, version: Version, status: Union[StatusCode, Status],
                 headers: List[SipHeader] = None,
                 body: Optional[Body] = None):
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

        return request_header.compose() + '\r\n' + super().compose()

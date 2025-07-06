from typing import Optional, Any

from ..sdp.message import SdpMessage
from ..sdp.parser import parse_sdp
from .message import Body, T


class CustomBody(Body[str]):

    def __init__(self, body: Optional[str] = None, content_type: Optional[str] = None):
        self._body = body
        self._content_type = content_type

    @property
    def value(self) -> T:
        return self._body

    @property
    def content_type(self) -> Optional[str]:
        return self._content_type

    def load_value(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        self._body = value
        return True

    def parse_from(self, data: str):
        self._body = data

    def compose(self) -> str:
        return self._body


class SdpBody(Body[SdpMessage]):

    def __init__(self, message: Optional[SdpMessage] = None):
        self._message = message

    @property
    def value(self) -> T:
        return self._message

    @property
    def content_type(self) -> Optional[str]:
        return 'application/sdp'

    def load_value(self, value: Any) -> bool:
        if not isinstance(value, SdpMessage):
            return False
        self._message = value
        return True

    def parse_from(self, data: str):
        self._message = parse_sdp(data)

    def compose(self) -> str:
        return self._message.compose()


BODIES = [SdpBody]


def wrap_body(data: Any, content_type: Optional[str] = None) -> Optional[Body]:
    if data is None:
        return None

    for body_cls in BODIES:
        body_cls = body_cls()
        if body_cls.load_value(data):
            return body_cls

    if isinstance(data, str):
        return CustomBody(data, content_type)

    raise ValueError('Unsupported body type ' + type(data))

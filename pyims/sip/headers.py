from abc import ABC, abstractmethod
from typing import Optional, Dict
import re

from ..nio.inet import InetAddress
from .sip_types import (
    Method, Version, Status,
    AuthenticationScheme, AuthenticationAlgorithm,
    STATUS_FROM_NUMBER, VERSIONS_BY_STR, AUTH_SCHEME_BY_STR, AUTH_ALGO_BY_STR
)


class Header(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def parse_from(self, value: str):
        pass

    @abstractmethod
    def compose(self)-> str:
        pass

    def __str__(self):
        return self.compose()

    def __repr__(self):
        return self.compose()


class IdentityHeader(Header, ABC):

    def __init__(self, value: Optional[str] = None):
        self.value: Optional[str] = value

    def parse_from(self, value: str):
        self.value = value

    def compose(self) -> str:
        return self.value


class IntHeader(Header, ABC):

    def __init__(self, value: Optional[int] = None):
        self.value: Optional[int] = value

    def parse_from(self, value: str):
        self.value = int(value)

    def compose(self) -> str:
        return f"{self.value}"


class CustomHeader(IdentityHeader):

    def __init__(self, name: str, value: str):
        super().__init__(value)
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class SenderSendeeHeader(Header, ABC):

    def __init__(self, visible_name: Optional[str] = None, uri: Optional[str] = None, tag: Optional[str] = None):
        self.visible_name: Optional[str] = visible_name
        self.uri: Optional[str] = uri
        self.tag: Optional[str] = tag

    def parse_from(self, value: str):
        match = re.search(r"^(?:(.+)\s)?<(.+)>(?:;tag=(.+))?$", value)
        assert match is not None, f"Invalid '{self.name}' header: {value}"
        self.visible_name = match.group(1)
        self.uri = match.group(2)
        self.tag = match.group(3)

    def compose(self) -> str:
        res = ''
        if self.visible_name:
            res += self.visible_name + ' '
        if self.uri:
            res += f"<{self.uri}>"
        if self.tag:
            res += f";tag={self.tag}"

        return res.strip()


class Request(Header):

    def __init__(self, method: Optional[Method] = None, uri: Optional[str] = None, version: Optional[Version] = None):
        self.method: Optional[Method] = method
        self.uri: Optional[str] = uri
        self.version: Optional[Version] = version

    @property
    def name(self) -> str:
        return 'Request'

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) == 3
        self.method = Method[value[0]]
        self.uri = value[1]
        self.version = VERSIONS_BY_STR[value[2]]


    def compose(self) -> str:
        return f"{self.method.name} {self.uri} {self.version.value}"


class Response(Header):

    def __init__(self, version: Optional[Version] = None, status: Optional[Status] = None):
        self.version: Optional[Version] = version
        self.status: Optional[Status] = status

    @property
    def name(self) -> str:
        return 'Response'

    def parse_from(self, value: str):
        value = value.split(" ", 2)
        assert len(value) == 3
        self.version = VERSIONS_BY_STR[value[0]]
        self.status = Status(STATUS_FROM_NUMBER[int(value[1])], value[2])

    def compose(self) -> str:
        return f"{self.version.value} {self.status.code.value[0]} {self.status.description}"


class CSeq(Header):

    def __init__(self, method: Optional[Method] = None, sequence: Optional[int] = None):
        self.method: Optional[Method] = method
        self.sequence: Optional[int] = sequence

    @property
    def name(self) -> str:
        return 'CSeq'

    def parse_from(self, value: str):
        value = value.split(" ")
        self.sequence = int(value[0])
        self.method = Method[value[1]]

    def compose(self) -> str:
        return f"{self.sequence} {self.method.name}"


class CallID(IdentityHeader):

    @property
    def name(self) -> str:
        return "Call-ID"


class From(SenderSendeeHeader):

    @property
    def name(self) -> str:
        return "From"


class To(SenderSendeeHeader):

    @property
    def name(self) -> str:
        return "To"


class ContentLength(IntHeader):

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)

    @property
    def name(self) -> str:
        return "Content-Length"


class MaxForwards(IntHeader):

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)

    @property
    def name(self) -> str:
        return "Max-Forwards"


class Expires(IntHeader):

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)

    @property
    def name(self) -> str:
        return "Expires"


class Contact(Header):

    def __init__(self, address: Optional[InetAddress] = None,
                 internal_tags: Optional[Dict[str, str]] = None,
                 external_tags: Optional[Dict[str, str]] = None):
        self.address = address
        self.internal_tags = internal_tags
        self.external_tags = external_tags

    @property
    def name(self) -> str:
        return 'Contact'

    def parse_from(self, value: str):
        match = re.search(r"^<sip:(.+):(\d+)(?:;(.*))?>(?:;(.*))?$", value)
        assert match is not None, f"Invalid '{self.name}' header: {value}"
        self.address = InetAddress(match.group(1), int(match.group(2)))
        self.internal_tags = self._breakup_tags(match.group(3))
        self.external_tags = self._breakup_tags(match.group(4))

    def compose(self) -> str:
        return f"<sip:{self.address.ip}:{self.address.port}{self._compose_tags(self.internal_tags)}>{self._compose_tags(self.external_tags)}"

    def _breakup_tags(self, tags: Optional[str]) -> Dict[str, str]:
        parsed = dict()
        if tags is None:
            return parsed

        for tag in tags.split(';'):
            if '=' in tag:
                vals = tag.split('=', 1)
                parsed[vals[0]] = vals[1]
            else:
                parsed[tag] = None

        return parsed

    def _compose_tags(self, tags: Optional[Dict[str, str]]) -> str:
        if tags is None:
            return ''

        return ';' + ';'.join([f"{k}={v}" if v is not None else k for k,v in tags.items()])


class Via(Header):

    def __init__(self, version: Optional[Version] = None,
                 transport: Optional[str] = None,
                 address: Optional[InetAddress] = None,
                 rport: Optional[str] = None,
                 branch: Optional[str] = None):
        self.version: Optional[Version] = version
        self.transport: Optional[str] = transport
        self.address: Optional[InetAddress] = address
        self.rport: Optional[str] = rport
        self.branch: Optional[str] = branch

    @property
    def name(self) -> str:
        return 'Via'

    def parse_from(self, value: str):
        match = re.search(r"^(SIP/\d+\.\d+)/(\w+)\s(.+)(?:;rport=(.+))?(?:;branch=(.+))?$", value)
        assert match is not None, f"Invalid '{self.name}' header: {value}"
        self.version = VERSIONS_BY_STR[match.group(1)]
        self.transport = match.group(2)
        self.address = InetAddress(*match.group(3).split(':', 1))
        self.rport = match.group(4)
        self.branch = match.group(5)

    def compose(self) -> str:
        res = f"{self.version.value}/{self.transport} {self.address.ip}:{self.address.port}"
        if self.rport:
            res += f";rport={self.rport}"
        if self.branch:
            res += f";branch={self.branch}"
        return res


class Authorization(Header):

    def __init__(self,
                 scheme: Optional[AuthenticationScheme] = None,
                 username: Optional[str] = None,
                 uri: Optional[str] = None,
                 realm: Optional[str] = None,
                 algorithm: Optional[AuthenticationAlgorithm] = None,
                 qop: Optional[str] = None,
                 nc: Optional[str] = None,
                 cnonce: Optional[str] = None,
                 nonce: Optional[str] = None,
                 response: Optional[str] = None,
                 additional_values: Optional[Dict[str, str]] = None):
        self.scheme: Optional[AuthenticationScheme] = scheme
        self.username: Optional[str] = username
        self.uri: Optional[str] = uri
        self.realm: Optional[str] = realm
        self.algorithm: Optional[AuthenticationAlgorithm] = algorithm
        self.qop: Optional[str] = qop
        self.nc: Optional[str] = nc
        self.cnonce: Optional[str] = cnonce
        self.nonce: Optional[str] = nonce
        self.response: Optional[str] = response
        self.additional_values: Optional[Dict[str, str]] = additional_values

    @property
    def name(self) -> str:
        return 'Authorization'

    def parse_from(self, value: str):
        value = value.split(' ', 1)
        self.scheme = AUTH_SCHEME_BY_STR[value[0]]

        values = [line.strip().split('=', 1) for line in value[1].split(', ')]
        values = {k: v.strip('"') for k, v in values}

        self.username = values.pop('username')
        self.uri = values.pop('uri')
        self.realm = values.pop('realm')
        self.algorithm = AUTH_ALGO_BY_STR[values.pop('algorithm')]
        self.qop = values.pop('qop')
        self.nc = values.pop('nc')
        self.cnonce = values.pop('cnonce')
        self.nonce = values.pop('nonce')
        self.response = values.pop('response')

        self.additional_values = values

    def compose(self) -> str:
        values = dict()

        values['username'] = self.username
        values['uri'] = self.uri
        values['realm'] = self.realm

        if self.cnonce:
            values['cnonce'] = self.cnonce
        if self.nonce:
            values['nonce'] = self.nonce
        if self.response:
            values['response'] = self.response

        if self.additional_values is not None:
            values.update(self.additional_values)

        values = ','.join([f"{k}=\"{v}\"" for k, v in values.items()])
        if self.qop:
            values += f",qop={self.qop}"
        if self.nc:
            values += f",nc={self.nc}"
        if self.algorithm:
            values += f",algorithm={self.algorithm.value}"

        return f"{self.scheme.value} {values}"


class WWWAuthenticate(Header):

    def __init__(self, scheme: Optional[AuthenticationScheme] = None,
                 nonce: Optional[str] = None, realm: Optional[str] = None,
                 algorithm: Optional[AuthenticationAlgorithm] = None, qop: Optional[str] = None,
                 additional_values: Optional[Dict[str, str]] = None):
        self.scheme: Optional[AuthenticationScheme] = scheme
        self.nonce: Optional[str] = nonce
        self.realm: Optional[str] = realm
        self.algorithm: Optional[AuthenticationAlgorithm] = algorithm
        self.qop: Optional[str] = qop
        self.additional_values: Optional[Dict[str, str]] = additional_values

    @property
    def name(self) -> str:
        return 'WWW-Authenticate'

    def parse_from(self, value: str):
        value = value.split(' ', 1)
        self.scheme = AUTH_SCHEME_BY_STR[value[0]]

        values = [line.strip().split('=', 1) for line in value[1].split(', ')]
        values = {k: v.strip('"') for k, v in values}

        self.nonce = values.pop('nonce')
        self.realm = values.pop('realm')
        self.algorithm = AUTH_ALGO_BY_STR[values.pop('algorithm')]
        self.qop = values.pop('qop')

        self.additional_values = values

    def compose(self) -> str:
        values = dict()

        values['nonce'] = self.nonce
        values['realm'] = self.realm
        values['algorithm'] = self.algorithm.value
        values['qop'] = self.qop

        if self.additional_values is not None:
            values.update(self.additional_values)

        values = ','.join([f"{k}=\"{v}\"" for k, v in values.items()])

        return f"{self.scheme.value} {values}"


HEADERS = [CSeq, CallID, From, To, Contact, ContentLength, MaxForwards, Expires, Via, Authorization, WWWAuthenticate]

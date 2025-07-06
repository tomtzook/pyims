from abc import ABC
from typing import Optional, Dict
import re

from ..nio.inet import InetAddress
from .sip_types import (
    Method, Version, Status,
    AuthenticationScheme, AuthenticationAlgorithm,
    STATUS_FROM_NUMBER, VERSIONS_BY_STR, AUTH_SCHEME_BY_STR, AUTH_ALGO_BY_STR
)
from ..util import Header


class SipHeader(Header, ABC):
    pass


class IdentityHeader(SipHeader, ABC):

    def __init__(self, value: Optional[str] = None):
        self.value: Optional[str] = value

    def parse_from(self, value: str):
        self.value = value

    def compose(self) -> str:
        return self.value


class IntHeader(SipHeader, ABC):

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


class SenderSendeeHeader(SipHeader, ABC):

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


class Request(SipHeader):
    __NAME__ = 'Request'

    def __init__(self, method: Optional[Method] = None, uri: Optional[str] = None, version: Optional[Version] = None):
        self.method: Optional[Method] = method
        self.uri: Optional[str] = uri
        self.version: Optional[Version] = version

    def parse_from(self, value: str):
        value = value.split(" ")
        assert len(value) == 3
        self.method = Method[value[0]]
        self.uri = value[1]
        self.version = VERSIONS_BY_STR[value[2]]


    def compose(self) -> str:
        return f"{self.method.name} {self.uri} {self.version.value}"


class Response(SipHeader):
    __NAME__ = 'Response'

    def __init__(self, version: Optional[Version] = None, status: Optional[Status] = None):
        self.version: Optional[Version] = version
        self.status: Optional[Status] = status

    def parse_from(self, value: str):
        value = value.split(" ", 2)
        assert len(value) == 3
        self.version = VERSIONS_BY_STR[value[0]]
        self.status = Status(STATUS_FROM_NUMBER[int(value[1])], value[2])

    def compose(self) -> str:
        return f"{self.version.value} {self.status.code.value[0]} {self.status.description}"


class CSeq(SipHeader):
    __NAME__ = 'CSeq'

    def __init__(self, method: Optional[Method] = None, sequence: Optional[int] = None):
        self.method: Optional[Method] = method
        self.sequence: Optional[int] = sequence

    def parse_from(self, value: str):
        value = value.split(" ")
        self.sequence = int(value[0])
        self.method = Method[value[1]]

    def compose(self) -> str:
        return f"{self.sequence} {self.method.name}"


class CallID(IdentityHeader):
    __NAME__ = 'Call-ID'


class From(SenderSendeeHeader):
    __NAME__ = 'From'


class To(SenderSendeeHeader):
    __NAME__ = 'To'


class ContentLength(IntHeader):
    __NAME__ = 'Content-Length'

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)


class MaxForwards(IntHeader):
    __NAME__ = 'Max-Forwards'

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)


class Expires(IntHeader):
    __NAME__ = 'Expires'

    def __init__(self, value: Optional[int] = None):
        super().__init__(value)


class Contact(SipHeader):
    __NAME__ = 'Contact'

    def __init__(self, address: Optional[InetAddress] = None,
                 internal_tags: Optional[Dict[str, str]] = None,
                 external_tags: Optional[Dict[str, str]] = None):
        self.address = address
        self.internal_tags = internal_tags
        self.external_tags = external_tags

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


class Via(SipHeader):
    __NAME__ = 'Via'

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


class RecordRoute(SipHeader):
    __NAME__ = 'Record-Route'

    def __init__(self,
                 user_info: Optional[str] = None,
                 host_ip: Optional[str] = None,
                 params: Optional[Dict[str, str]] = None):
        self.user_info = user_info
        self.host_ip = host_ip
        self.params = params

    def parse_from(self, value: str):
        match = re.search(r"^<sip:(.+)?@(.+)(?:;(.+))?>$", value)
        assert match is not None, f"Invalid '{self.name}' header: {value}"
        self.user_info = match.group(1)
        self.host_ip = match.group(2)

        params = match.group(3)
        if params is not None:
            params = [param.split('=', 1) for param in params.split(';')]
            self.params = {param[0]: param[1] for param in params}
        else:
            self.params = None

    def compose(self) -> str:
        res = '<sip:'
        if self.user_info:
            res += f'{self.user_info}@'
        res += self.host_ip
        if self.params:
            res += ';' + ';'.join([f"{k}={v}" for k,v in self.params.items()])
        return res


class Authorization(SipHeader):
    __NAME__ = 'Authorization'

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


class WWWAuthenticate(SipHeader):
    __NAME__ = 'WWW-Authenticate'

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


HEADERS = [CSeq, CallID, From, To, Contact, ContentLength, MaxForwards, Expires, Via, RecordRoute, Authorization, WWWAuthenticate]

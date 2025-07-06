from typing import Dict, List, Optional, Tuple

from .headers import HEADERS, Request, Header, CustomHeader
from .sip_types import MessageType, METHODS, VERSIONS_BY_STR
from .headers import Response
from .message import RequestMessage, ResponseMessage, Message, Body
from .bodies import BODIES, CustomBody


def _read_headers(data: str):
    lines = data.split("\r\n")

    headers = dict()
    for line in lines[1:]:
        if len(line.strip()) < 1:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in headers:
            headers[key].append(value)
        else:
            headers[key] = [value]

    return lines[0], headers


def _get_body_length(headers: List[Header]) -> int:
    length_headers = [header for header in headers if header.name == 'Content-Length']
    if len(length_headers) < 1:
        return 0

    # noinspection PyUnresolvedReferences
    return length_headers[0].value


def _get_content_type(headers: List[Header]) -> Optional[str]:
    headers = [header for header in headers if header.name == 'Content-Type']
    if len(headers) < 1:
        return None

    # noinspection PyUnresolvedReferences
    return headers[0].value


def _parse_header(top_header: str, headers: Dict[str, List[str]]):
    parsed_headers = list()
    message_type = None
    type_header = None

    for header_cls in HEADERS:
        header = header_cls()
        if header.name not in headers:
            continue

        for value in headers[header.name]:
            header = header_cls()
            header.parse_from(value)
            parsed_headers.append(header)

    type_line = top_header.split(" ")
    if type_line[0] in METHODS:
        # this is a request
        request = Request()
        request.parse_from(top_header)

        message_type = MessageType.REQUEST
        type_header = request
    elif type_line[0] in VERSIONS_BY_STR.keys():
        # this is a response
        response = Response()
        response.parse_from(top_header)

        message_type = MessageType.RESPONSE
        type_header = response
    else:
        # what?
        raise AssertionError('message type could not be determined')

    return message_type, type_header, parsed_headers


def parse_body(body_str: str, body_len: int, content_type: Optional[str]) -> Optional[Body]:
    if body_len < 1:
        return None

    if content_type is None:
        return CustomBody(body_str)

    for body_cls in BODIES:
        body_cls = body_cls()
        if body_cls.content_type == content_type:
            body_cls.parse_from(body_str)
            return body_cls

    return CustomBody(body_str, content_type)


def parse(data: str, start_idx: int = 0) -> Tuple[Message, int]:
    headers_end = data.find("\r\n\r\n", start_idx)
    if headers_end < 0:
        headers_end = len(data)

    top_header, raw_headers = _read_headers(data[start_idx:headers_end])
    message_type, type_header, parsed_headers = _parse_header(top_header, raw_headers)

    body_len = _get_body_length(parsed_headers)
    body = data[start_idx+headers_end+1:start_idx+headers_end+1+body_len] if body_len > 1 else ''

    for name, values in raw_headers.items():
        if not any([header for header in parsed_headers if name == header.name]):
            parsed_headers.extend([CustomHeader(name, value) for value in values])

    body = parse_body(body, body_len, _get_content_type(parsed_headers))

    total_size = headers_end - start_idx + len('\r\n\r\n') + body_len

    if message_type == MessageType.REQUEST:
        return RequestMessage(type_header.version, type_header.method, type_header.uri, headers=parsed_headers, body=body), total_size
    elif message_type == MessageType.RESPONSE:
        return ResponseMessage(type_header.version, type_header.status, headers=parsed_headers, body=body), total_size
    else:
        raise AssertionError('message type could not be determined')

from typing import Dict, List

from pyims.sip.headers import HEADERS, Request, Header, CustomHeader
from pyims.sip.sip_types import MessageType, METHODS, VERSIONS_BY_STR
from pyims.sip.headers import Response
from pyims.sip.message import RequestMessage, ResponseMessage, Message


def _read_headers(data: str):
    lines = data.split("\r\n")

    headers = dict()
    for line in lines[1:]:
        if len(line.strip()) < 1:
            continue

        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()

    return lines[0], headers


def _get_body_length(headers: List[Header]) -> int:
    length_headers = [header for header in headers if header.name == 'Content-Length']
    if len(length_headers) < 1:
        return 0

    # noinspection PyUnresolvedReferences
    return length_headers[0].value


def _parse_header(top_header: str, headers: Dict[str, str]):
    parsed_headers = list()
    message_type = None
    type_header = None

    for header in HEADERS:
        header = header()
        if header.name not in headers:
            continue

        header.parse_from(headers[header.name])
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


def parse(data: str, start_idx: int = 0) -> Message:
    headers_end = data.find("\r\n\r\n", start_idx)
    if headers_end < 0:
        headers_end = len(data)

    top_header, raw_headers = _read_headers(data[start_idx:headers_end])
    message_type, type_header, parsed_headers = _parse_header(top_header, raw_headers)

    body_len = _get_body_length(parsed_headers)
    body = data[start_idx+headers_end+1:start_idx+headers_end+1+body_len] if body_len > 1 else ''

    for name, value in raw_headers.items():
        if name not in parsed_headers:
            parsed_headers.append(CustomHeader(name, value))

    if message_type == MessageType.REQUEST:
        return RequestMessage(type_header.version, type_header.method, type_header.uri, headers=parsed_headers, body=body)
    elif message_type == MessageType.RESPONSE:
        return ResponseMessage(type_header.version, type_header.status, headers=parsed_headers, body=body)
    else:
        raise AssertionError('message type could not be determined')

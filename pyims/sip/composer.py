from typing import List, Union

from pyims.sip.headers import Header
from pyims.sip.message import RequestMessage, ResponseMessage
from pyims.sip.sip_types import Version, Method, Status, StatusCode


def compose_request(version: Version, method: Method, server_uri: str, body: str, headers: List[Header] = None) -> str:
    if headers is None:
        headers = list()

    return RequestMessage(version, method, server_uri, headers, body).compose()


def compose_response(version: Version, status: Union[StatusCode, Status], headers: List[Header] = None) -> str:
    if headers is None:
        headers = list()

    return ResponseMessage(version, status, headers).compose()

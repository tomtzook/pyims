from .fields import FIELDS
from .message import SdpMessage


def parse_sdp(data: str) -> SdpMessage:
    props = dict()
    for line in data.split('\r\n'):
        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        if key in props:
            if isinstance(props[key], list):
                props[key].append(value)
            else:
                props[key] = [props[key], value]
        else:
            props[key] = value

    fields = dict()
    for field_cls in FIELDS:
        field = field_cls()
        if field.name not in props:
            continue

        values = props[field.name]
        if isinstance(values, list):
            parsed = []
            for v in values:
                field = field_cls()
                field.parse_from(v)
                parsed.append(field)
        else:
            field.parse_from(values)
            parsed = field

        fields[field.name] = parsed

    return SdpMessage(fields)

from typing import Union, Optional, List, Dict

from .fields import SdpField, AttributeField
from .attributes import Attribute


class SdpMessage(object):

    def __init__(self,
                 fields: Optional[Union[List[SdpField], Dict[str, SdpField]]] = None,
                 attributes: Optional[List[Attribute]] = None):
        if fields is None:
            self._fields = dict()
        elif isinstance(fields, list):
            self._fields = dict()
            [self.add_field(field) for field in fields]
        else:
            self._fields = fields

        if attributes is not None:
            [self.add_field(AttributeField(attr)) for attr in attributes]


    def field(self, name: Union[str, type]) -> SdpField:
        if isinstance(name, str):
            return self._fields[name]
        else:
            return self._fields[name.__NAME__]

    def add_field(self, field: SdpField):
        if field.name in self._fields:
            f = self._fields[field.name]
            if isinstance(f, list):
                f.append(field)
            elif f.can_have_multiple:
                self._fields[field.name] = [f, field]
            else:
                raise ValueError('cannot add field because existing')
        else:
            self._fields[field.name] = field

    def compose(self) -> str:
        lst = []
        for fields in self._fields.values():
            if isinstance(fields, list):
                for field in fields:
                    lst.append(f"{field.name}={field.compose()}")
            else:
                field = fields
                lst.append(f"{field.name}={field.compose()}")

        return '\r\n'.join(lst)

    def __str__(self):
        return self.compose()

    def __repr__(self):
        return self.compose()

from typing import Union, Optional, List, Dict, TypeVar

from .fields import SdpField, AttributeField
from .attributes import Attribute


class SdpMessage(object):
    T = TypeVar('T')

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


    def field(self, name: Union[str, T]) -> T:
        wanted_name = name if isinstance(name, str) else name.__NAME__
        return self._fields[wanted_name]

    def attribute(self, name: Union[str, T]) -> List[T]:
        wanted_name = name if isinstance(name, str) else name.__NAME__

        lst = []
        for fields in self._fields.values():
            if not isinstance(fields, list):
                fields = [fields]

            for field in fields:
                if not isinstance(field, AttributeField):
                    continue

                if field.attribute.name == wanted_name:
                    lst.append(field.attribute)

        return lst


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

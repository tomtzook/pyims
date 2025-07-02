from typing import Dict, Any


def dict_to_namedtuple(tuple_type: Any, data: Dict[str, Any]) -> Any:
    tuple_data = {name: None for name in tuple_type._fields}
    tuple_data.update(data)

    return tuple_type(**tuple_data)

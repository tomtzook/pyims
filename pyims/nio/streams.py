from abc import ABC, abstractmethod
from typing import Callable, TypeVar, Generic, Optional
from typing_extensions import ParamSpec


T = TypeVar('T')
P = ParamSpec('P')


class ReadableStream(ABC, Generic[P]):

    @abstractmethod
    def start_read(self, callback: Callable[[Optional[P]], None]):
        pass


class WritableStream(ABC, Generic[T]):

    @abstractmethod
    def write(self, data: T):
        pass

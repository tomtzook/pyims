from abc import ABC, abstractmethod
from typing import Optional


class Header(ABC):
    __NAME__: Optional[str] = None

    @property
    def name(self) -> str:
        return self.__NAME__

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


Field = Header

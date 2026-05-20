from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def write_file(self, path: str, content: str) -> None: ...

    @abstractmethod
    def read_file(self, path: str) -> str: ...

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[str]: ...

    @abstractmethod
    def delete_file(self, path: str) -> None: ...

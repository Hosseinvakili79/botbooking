from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ClickResult:
    success: bool
    error: str = ""


class InputBackend(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def click(self, x: int, y: int, button: str, click_type: str) -> ClickResult: ...

    @abstractmethod
    def stop(self) -> None: ...


class UnsupportedInputBackend(InputBackend):
    def start(self) -> None:
        raise RuntimeError("No supported input backend is available")

    def click(self, x: int, y: int, button: str, click_type: str) -> ClickResult:
        return ClickResult(False, "No supported input backend is available")

    def stop(self) -> None:
        return

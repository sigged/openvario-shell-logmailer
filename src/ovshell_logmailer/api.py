from abc import abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from typing_extensions import Protocol

class Mailer(Protocol):
    
    @abstractmethod
    def send_email_with_attachment(self, sender, recipient, subject, body, attachment_path):
        """Send an email with an attachment"""
        pass  # pragma: nocover

@dataclass
class LogFilter:
    igc: bool = True
    nmea: bool = False

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def fromdict(cls, state: dict[str, Any]) -> "LogFilter":
        filt = cls()
        if "igc" in state:
            filt.igc = state["igc"]
        if "nmea" in state:
            filt.nmea = state["nmea"]
        return filt


@dataclass
class FileInfo:
    name: str
    ftype: str
    size: int
    mtime: float
    downloaded: bool


class LogRepository(Protocol):

    @abstractmethod
    def get_logspath(self) -> str:
        pass  # pragma: nocover

    @abstractmethod
    def list_logs(self, filter: LogFilter) -> list[FileInfo]:
        pass  # pragma: nocover



import os

from .api import LogRepository, LogFilter, FileInfo


class LogRepositoryImpl(LogRepository):
    """Object that handles lists and filters log files"""

    def __init__(self, source_dir: str) -> None:
        self.source_dir = source_dir

    def get_logspath(self) -> list[FileInfo]:
        return self.source_dir

    def list_logs(self, filter: LogFilter) -> list[FileInfo]:
        if not os.path.exists(self.source_dir):
            return []
        downloaded = []
        res = []

        for entry in os.scandir(self.source_dir):
            _, fext = os.path.splitext(entry.name.lower())
            fileinfo = FileInfo(
                name=entry.name,
                ftype=fext,
                size=entry.stat().st_size,
                mtime=entry.stat().st_mtime,
                downloaded=entry.name.lower() in downloaded,
            )
            if self._matches(fileinfo, filter):
                res.append(fileinfo)
        return sorted(res, key=lambda fi: fi.mtime, reverse=True)

    def _matches(self, fileinfo: FileInfo, filter: LogFilter) -> bool:
        ftypes = [".nmea" if filter.nmea else None, ".igc" if filter.igc else None]
        matches = fileinfo.ftype in ftypes
        return matches


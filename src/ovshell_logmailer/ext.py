from typing import Sequence

from ovshell import api
from ovshell_logmailer.logemailerapp import LogEmailerApp


class LogMailerExtension(api.Extension):
    title = "Log Mailer"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [
            LogEmailerApp(self.shell)
        ]

"""Log emailer extension"""

import ovshell.api
from ovshell_logmailer import ext


def extension(id: str, shell: ovshell.api.OpenVarioShell) -> ovshell.api.Extension:
    return ext.LogMailerExtension(id, shell)

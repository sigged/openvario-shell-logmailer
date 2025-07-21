import os, urwid

from typing import Dict
from ovshell import api, widget

from .api import Mailer, LogRepository, LogFilter, FileInfo
from .logrepository import LogRepositoryImpl
from .mailer import SmtpMailer
from .utils import format_size

EMAIL_CONFIG = "~/ovshell-logmailer.conf"
DEFAULT_EMAIL_CONFIG = {
    "SMTPHOST": "smtp.example.com",
    "SMTPPORT": "587",
    "SMTPUSER": "yourusername",
    "SMTPPASS": "yourpassword",
    "USETLS": "True",
    "SENDER": "sender@yourdomain.com",
    "EMAILS": "alice@example.com,bob@example.com",
    "EMAILTITLE": "Your flight {FILENAME}",
    "EMAILBODY": "Open Vario sent you this log file: {FILENAME}.<br>You can find it attached to this e-mail."
}


class LogEmailerApp(api.App):
    name = "email-logs"
    title = "E-mail Logs"
    description = "E-mail flight logs"
    priority = 50

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        self.config_path = os.path.expanduser(EMAIL_CONFIG)

    def launch(self) -> None:
        xcsdir = os.environ.get("XCSOAR_HOME", "/home/root/.xcsoar")
        self.logspath = os.path.join(xcsdir, "logs")
        logrepository = LogRepositoryImpl(self.logspath)

        email_config = self.parse_conf();

        mailer = SmtpMailer(
            email_config["SMTPHOST"],
            email_config["SMTPPORT"],
            email_config["SMTPUSER"],
            email_config["SMTPPASS"],
            email_config["USETLS"],
        )
        
        act = LogEmailerActivity(logrepository, mailer, email_config, self.shell)
        self.shell.screen.push_activity(act)

    def create_default_conf(self):
        """ Create a default configuration file """

        with open(self.config_path, "w") as f:
            for key, value in DEFAULT_EMAIL_CONFIG.items():
                f.write(f"{key}={value}\n")


    def parse_conf(self):
        config = {}
        try:
            with open(self.config_path, "r") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if '=' not in line:
                        raise ValueError(f"Line {lineno}: Missing '=' in line")
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "EMAILS":
                        config[key] = [email.strip() for email in value.split(",") if email.strip()]
                    elif key == "SMTPPORT":
                        config[key] = int(value)
                    elif key == "USETLS":
                        config[key] = value.lower() == "true"
                    else:
                        config[key] = value
            # Validate required keys
            for required_key in DEFAULT_EMAIL_CONFIG:
                if required_key not in config:
                    raise KeyError(f"Missing required config key: {required_key}")
        except Exception as e:
            try:
                self.create_default_conf()
                self.shell.screen.set_status(("remark", f"Recreated default configuration file"))
                return self.parse_conf()
            except Exception as e:
                self.shell.screen.set_status(("error message", f"Error creating file {self.config_path}: {e}"))
        return config


class LogEmailerActivity(api.Activity):
    _dl_in_progress: dict[str, urwid.WidgetPlaceholder]
    filter: LogFilter

    def __init__(
        self,
        logrepository: "LogRepository",
        mailer: "Mailer",
        email_config: dict,
        shell: api.OpenVarioShell,
    ) -> None:
        self.shell = shell
        self.logrepository = logrepository
        self.mailer = mailer
        self.email_config = email_config
        self._dl_in_progress = {}

    def create(self) -> urwid.Widget:
        filtstate = self.shell.settings.get("fileman.download_logs.filter", dict) or {}
        self.filter = LogFilter.fromdict(filtstate)

        self._file_walker = urwid.SimpleFocusListWalker([])
        self._app_view = self._create_app_view()

        self.frame = urwid.Frame(
            self._create_app_view(), header=widget.ActivityHeader("E-mail Flight Logs")
        )
        return self.frame

    def activate(self) -> None:
        self._populate_file_list()
        self._dl_in_progress = {}

    
    def _create_app_view(self) -> urwid.Widget:
        file_filter = self._make_filter()

        return urwid.Pile(
            [
                ("pack", file_filter),
                ("pack", urwid.Divider()),
                urwid.ListBox(self._file_walker),
            ]
        )

    def _mounted(self, wdg) -> None:
        self._populate_file_list()
        self._dl_in_progress = {}

    def _make_filter(self) -> urwid.Widget:
        options = urwid.GridFlow(
            [
                self._make_filter_checkbox("*.igc", "igc"),
                self._make_filter_checkbox("*.nmea", "nmea"),
            ],
            cell_width=12,
            h_sep=2,
            v_sep=1,
            align="left",
        )
        return urwid.LineBox(options, "Options", title_align="left")

    def _populate_file_list(self) -> None:
        files = self.logrepository.list_logs(self.filter)
        
        if files:
            file_items = [self._make_file_picker(de) for de in files]
        else:
            file_items = [urwid.Text(("remark", "No flight logs selected."))]

        del self._file_walker[:]
        self._file_walker.extend(file_items)
        self._file_walker.set_focus(0)

    def _make_filter_checkbox(self, title: str, attr: str) -> urwid.Widget:
        checked = getattr(self.filter, attr)
        cb = urwid.CheckBox(title, checked)
        urwid.connect_signal(cb, "change", self._set_filter_option, user_args=[attr])
        return cb

    def _set_filter_option(self, attr: str, w: urwid.Widget, state: bool) -> None:
        setattr(self.filter, attr, state)
        self.shell.settings.set("fileman.download_logs.filter", self.filter.asdict())
        self.shell.settings.save()
        self._populate_file_list()

    def _make_file_picker(self, fileinfo: FileInfo) -> urwid.Widget:
        fmtsize = format_size(fileinfo.size)
        file_cols = urwid.Columns(
            [
                ("weight", 2, urwid.Text(fileinfo.name)),
                ("weight", 1, urwid.Text(fmtsize + " ", align="right")),
            ]
        )
        w = widget.SelectableItem(file_cols)

        urwid.connect_signal(
            w, "click", self._display_maildialog, user_args=[fileinfo]
        )
        return w

    def _display_maildialog(
        self, fileinfo: FileInfo, w: urwid.Widget
    ) -> None:
        
        sender = self.email_config["SENDER"]

        # --- OK and Cancel buttons at the bottom ---
        ok_btn = urwid.Button("Send", align='center')
        cancel_btn = urwid.Button("Cancel", align='center')

        # Button handlers
        def close_dialog(button):
            self.frame.body = self._app_view  # Restore the main view

        def send_mail_handler(button):

            # Get all selected email addresses from checkboxes
            selected_emails = []
            if hasattr(self, 'recipients_checkboxes'):
                for checkbox in self.recipients_checkboxes:
                    if checkbox.state:  # If checkbox is checked
                        selected_emails.append(checkbox.label)

            # Mark queued
            for recipient in selected_emails: 
                self.recipients_mailstate[recipient].set_text(("remark", "QUEUED"))

            self.shell.screen.draw()

            no_errors = True

            # Send email to each selected recipient
            for recipient in selected_emails: 
                self.recipients_mailstate[recipient].set_text(("success message", "SENDING..."))
                self.shell.screen.draw()

                try:
                    self._send_mail(sender, recipient, fileinfo)
                    self.recipients_mailstate[recipient].set_text(("success banner", "SENT"))
                except Exception as e:
                    self.recipients_mailstate[recipient].set_text(("error banner", "ERROR"))
                    self.shell.screen.set_status(("error message", f"Error: {e}"))
                    no_errors = False;
                finally:
                    self.shell.screen.draw()

            # Close the dialog if no errors
            if no_errors:
                close_dialog(button)

        urwid.connect_signal(ok_btn, "click", send_mail_handler)
        urwid.connect_signal(cancel_btn, "click", close_dialog)

        button_widget = urwid.Padding(
            urwid.Columns([
                ('weight', 1, urwid.Padding(urwid.AttrMap(cancel_btn, None, focus_map='btn focus'), left=2, right=2)),
            ], dividechars=2, focus_column=0), left=2, right=2)

        # --- Checkbox list for e-mail addresses ---
        emails = self.email_config["EMAILS"]

        content_widget = urwid.Padding(
            urwid.Pile([
                urwid.Text(("remark", "No e-mail recipients configured"), align="left"),
                urwid.Divider(),
                urwid.Divider(),
            ]), left=4, right=0)
        
        if(emails):
            recipient_addresses = self.email_config["EMAILS"]
            recipients_list = []
            self.recipients_checkboxes = []  # Store checkbox references
            self.recipients_mailstate: Dict[str, urwid.Text] = dict()  # Stores mailed recipients

            for recipient_address in recipient_addresses:

                # Create recipient checkbox and keep reference
                recipient_checkbox = urwid.CheckBox(recipient_address, False)
                self.recipients_checkboxes.append(recipient_checkbox)

                # Create recipient state widget and keep reference
                recipient_state = urwid.Text(("text", ""))
                self.recipients_mailstate[recipient_address] = recipient_state

                recipient_cols = urwid.Columns(
                    [
                        ("weight", 2, recipient_checkbox),
                        ("weight", 1, recipient_state),
                    ]
                )
                recipients_list.append(urwid.AttrMap(recipient_cols, None, focus_map='reversed'))

            recipients_pile = urwid.Pile(recipients_list)
            content_widget.original_widget = recipients_pile            
            button_widget.original_widget = urwid.Columns([
                    ('weight', 2, urwid.Padding(urwid.AttrMap(ok_btn, None, focus_map='btn focus'), left=2, right=2)),
                    ('weight', 1, urwid.Padding(urwid.AttrMap(cancel_btn, None, focus_map='btn focus'), left=2, right=2)),
                ])
        else:
            cancel_btn.set_label("Close")


        # --- Dialog layout ---
        pile = urwid.Pile([
            urwid.Text("E-mail recipients"),
            urwid.Divider(),
            content_widget,
            urwid.Divider(),
            urwid.Divider(),
            button_widget,
        ])
        

        boxed = urwid.LineBox(pile, title=fileinfo.name, title_align="center")
        overlay = urwid.Overlay(
            urwid.Filler(boxed, valign='middle'),
            self._app_view,
            align='center',
            width=('relative', 80),
            valign='middle',
            height=('relative', 60),
        )
        self.frame.body = overlay


    def _send_mail(self, sender: str, recipient: str, fileinfo: FileInfo) -> None:
        
        # Get correct file path
        filepath = os.path.join(self.logrepository.get_logspath(), fileinfo.name)

        # Send e-mail
        self.mailer.send_email_with_attachment(
            sender = sender, 
            recipient = recipient, 
            subject = self.email_config["EMAILTITLE"].format(FILENAME=fileinfo.name),
            body = self.email_config["EMAILBODY"].format(FILENAME=fileinfo.name),
            attachment_path = filepath
        )

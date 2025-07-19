import smtplib
import mimetypes

from email.message import EmailMessage
from .api import Mailer

class SmtpMailer(Mailer):
    def __init__(self, smtp_host, smtp_port, smtp_user, smtp_pass, use_tls):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.use_tls = use_tls

    def send_email_with_attachment(self, sender, recipient, subject, body, attachment_path):
        msg = EmailMessage()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.set_content(body)

        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)

        with open(attachment_path, 'rb') as f:
            msg.add_attachment(f.read(),
                               maintype=maintype,
                               subtype=subtype,
                               filename=attachment_path.split('/')[-1])

            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
            server.quit()
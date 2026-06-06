import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


def create_smtp_connection(sender_email, app_password):
    """Create and authenticate an SMTP connection to Gmail.
    
    Uses SMTP_SSL on port 465 for secure connection.
    Raises an exception if login fails.
    """
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
    server.login(sender_email, app_password)
    return server


def send_single_email(server, sender_email, recipient, subject, body,
                      attachment_bytes=None, attachment_filename=None):
    """Send a single email using an existing SMTP connection.
    
    Args:
        server: Active SMTP connection
        sender_email: Sender's email address
        recipient: Recipient's email address
        subject: Email subject line
        body: Email body (plain text)
        attachment_bytes: Optional file content as bytes to attach
        attachment_filename: Optional filename for the attachment
    
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach file if provided
        if attachment_bytes and attachment_filename:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment_filename}"'
            )
            msg.attach(part)

        server.send_message(msg)
        return True, None
    except smtplib.SMTPRecipientsRefused as e:
        return False, f'Recipient refused: {recipient}'
    except smtplib.SMTPException as e:
        return False, f'SMTP error: {str(e)}'
    except Exception as e:
        return False, f'Unexpected error: {str(e)}'


def close_connection(server):
    """Safely close an SMTP connection."""
    try:
        server.quit()
    except Exception:
        pass

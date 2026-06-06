import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def create_smtp_connection(sender_email, app_password):
    """Create and authenticate an SMTP connection to Gmail.
    
    Uses SMTP_SSL on port 465 for secure connection.
    Raises an exception if login fails.
    """
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
    server.login(sender_email, app_password)
    return server


def send_single_email(server, sender_email, recipient, subject, body):
    """Send a single email using an existing SMTP connection.
    
    Args:
        server: Active SMTP connection
        sender_email: Sender's email address
        recipient: Recipient's email address
        subject: Email subject line
        body: Email body (plain text)
    
    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

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

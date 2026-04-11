import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import settings

logger = logging.getLogger(__name__)

def send_notification_email(to_email: str, subject: str, message: str, link: str = None):
    """
    Sends an actual email using the SMTP configuration in settings.
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.MAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        body = message
        if link:
            body += f"\n\nLink: {link}"
        
        msg.attach(MIMEText(body, 'plain'))

        # Connect and send
        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        # Print for debugging in development if SMTP fails
        print(f"ERROR SENDING EMAIL: {e}")
        return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..core.config import settings

class EmailService:
    @staticmethod
    def _send_email(to_email: str, subject: str, body: str):
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.MAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
            server.starttls()
            clean_password = settings.MAIL_PASSWORD.replace(" ", "").strip() if settings.MAIL_PASSWORD else ""
            server.login(settings.MAIL_USERNAME, clean_password)
            text = msg.as_string()
            server.sendmail(settings.MAIL_FROM, to_email, text)
            server.quit()
            print(f"[EMAIL SERVICE] Sent to {to_email}")
            return True
        except Exception as e:
            print(f"[EMAIL SERVICE ERROR] Failed to send email: {e}")
            return False

    @staticmethod
    def send_welcome_email(email: str, user_id: int):
        subject = "Welcome to OccaServe! Complete your account setup"
        link = f"{settings.SITE_URL}/auth/set-password?uid={user_id}"
        body = f"""
        Welcome to OccaServe!
        
        Thank you for your booking! Your account has been created.
        Please click the link below to set your password:
        
        {link}
        
        Best regards,
        The OccaServe Team
        """
        return EmailService._send_email(email, subject, body)

    @staticmethod
    def send_booking_confirmation(email: str, booking_id: int):
        subject = f"Booking Request Received #{booking_id}"
        body = f"""
        Hello,
        
        We have received your booking request #{booking_id}.
        We will verify your ID and contact you shortly with further details.
        
        Thank you for choosing OccaServe.
        """
        return EmailService._send_email(email, subject, body)
    
    @staticmethod
    def send_verification_email(email: str, code: str):
        subject = "Verify your OccaServe Account"
        body = f"""
        Hello,
        
        Your verification code is: {code}
        
        Please enter this code to complete your registration.
        
        If you did not request this code, please ignore this email.
        """
        return EmailService._send_email(email, subject, body)

    @staticmethod
    def send_password_reset_email(email: str, token: str):
        subject = "Reset your OccaServe Password"
        link = f"{settings.SITE_URL}/auth/reset-password?token={token}"
        body = f"""
        Hello,
        
        We received a request to reset your password.
        Please click the link below to set a new password:
        
        {link}
        
        This link will expire in 1 hour.
        
        If you did not request this, please ignore this email.
        """
        return EmailService._send_email(email, subject, body)
    @staticmethod
    def send_caterer_account_created_email(email: str, password: str, business_name: str):
        subject = f"Welcome to OccaServe, {business_name}!"
        link = f"{settings.SITE_URL}/auth/login"
        body = f"""
        Hello {business_name},
        
        An admin has created a caterer account for you on OccaServe.
        You can now log in and start setting up your profile and packages.
        
        Your Login Credentials:
        Email: {email}
        Temporary Password: {password}
        
        Login here: {link}
        
        IMPORTANT: For security reasons, please change your password immediately after your first login.
        
        Best regards,
        The OccaServe Team
        """
        return EmailService._send_email(email, subject, body)

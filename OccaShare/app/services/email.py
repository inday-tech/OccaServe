import smtplib
import logging
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_email(to_email: str, subject: str, body: str, html_body: str = None):
        logger.info(f"[EMAIL SERVICE] Preparing to send email to {to_email} | subject: '{subject}'")
        from_email = settings.MAIL_FROM if settings.MAIL_FROM else settings.MAIL_USERNAME
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Attach plain text version
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach HTML version if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            logger.info(f"[EMAIL SERVICE] Connecting to SMTP server {settings.MAIL_SERVER}:{settings.MAIL_PORT}")
            if settings.MAIL_PORT == 465:
                server = smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT)
            else:
                server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
                server.starttls()
            
            clean_password = settings.MAIL_PASSWORD.replace(" ", "").strip() if settings.MAIL_PASSWORD else ""
            server.login(settings.MAIL_USERNAME, clean_password)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()
            logger.info(f"[EMAIL SERVICE] Email successfully sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL SERVICE ERROR] Failed to send email to {to_email}: {e}")
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
        subject = f"{code} is your OccaServe verification code"
        body = f"Hello,\n\nYour verification code is: {code}\n\nPlease enter this code to complete your registration.\n\nIf you did not request this code, please ignore this email."
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333; }}
                .header {{ background-color: #FF7B54; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #eee; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background-color: #fff; border: 2px dashed #FF7B54; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #FF7B54; letter-spacing: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #888; }}
                .btn {{ background-color: #FF7B54; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>OccaServe</h1>
                </div>
                <div class="content">
                    <h2>Verify Your Account</h2>
                    <p>Hello,</p>
                    <p>Thank you for joining OccaServe. To complete your registration, please use the following verification code:</p>
                    <div class="otp-box">
                        <div class="otp-code">{code}</div>
                    </div>
                    <p>This code will expire in 5 minutes. If you did not request this, you can safely ignore this email.</p>
                    <p>Best regards,<br>The OccaServe Team</p>
                </div>
                <div class="footer">
                    &copy; 2026 OccaServe Philippines. All rights reserved.
                </div>
            </div>
        </body>
        </html>
        """
        return EmailService._send_email(email, subject, body, html_body)

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

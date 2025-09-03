#!/usr/bin/env python3
"""
Email Service

Service for sending report emails via SMTP.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)

class EmailService:
    """Service for email operations"""
    
    def __init__(self, settings):
        self.settings = settings
        logger.info(f"Initialized Email service with SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    
    async def send_report_email(self, subject: str, body: str, recipients: List[str]) -> bool:
        """Send report email to recipients"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.settings.EMAIL_FROM
            message["To"] = ", ".join(recipients)
            
            # Add HTML body
            html_part = MIMEText(body, "html", "utf-8")
            message.attach(html_part)
            
            # Setup SMTP connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls(context=context)
                if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                    server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                
                # Send email
                server.sendmail(
                    self.settings.EMAIL_FROM,
                    recipients,
                    message.as_string()
                )
            
            logger.info(f"Successfully sent email to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=10) as server:
                server.starttls(context=context)
                if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                    server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                logger.info("SMTP connection test successful")
                return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
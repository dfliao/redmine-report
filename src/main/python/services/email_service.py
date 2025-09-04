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
from email import utils as email_utils
from typing import List

logger = logging.getLogger(__name__)

class EmailService:
    """Service for email operations"""
    
    def __init__(self, settings):
        self.settings = settings
        logger.info(f"Initialized Email service with SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    
    async def send_report_email(self, subject: str, body: str, recipients: List[str]) -> bool:
        """Send report email to recipients"""
        logger.info(f"Starting email send to {len(recipients)} recipients: {recipients}")
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.settings.EMAIL_FROM
            message["To"] = ", ".join(recipients)
            message["Date"] = email_utils.formatdate(localtime=True)
            
            # Add HTML body
            html_part = MIMEText(body, "html", "utf-8")
            message.attach(html_part)
            
            # Log SMTP settings (without password)
            logger.info(f"SMTP Settings - Host: {self.settings.SMTP_HOST}, Port: {self.settings.SMTP_PORT}")
            logger.info(f"From: {self.settings.EMAIL_FROM}")
            
            # Use the same SMTP configuration as Redmine
            # Port 587 with STARTTLS, login authentication, no SSL verification
            try:
                logger.info("Using Redmine-compatible SMTP settings (Port 587 + STARTTLS)")
                
                # Create SSL context with relaxed verification (same as Redmine)
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE  # Same as openssl_verify_mode: none
                
                with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=30) as server:
                    server.set_debuglevel(1)  # Enable debug output
                    
                    # Enable STARTTLS (same as enable_starttls_auto: true)
                    server.starttls(context=context)
                    logger.info("STARTTLS enabled")
                    
                    # Login authentication (same as authentication: :login)
                    if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                        logger.info(f"Logging in with username: {self.settings.SMTP_USERNAME}")
                        server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                        logger.info("SMTP login successful")
                    
                    # Send email
                    server.sendmail(
                        self.settings.EMAIL_FROM,
                        recipients,
                        message.as_string()
                    )
                    
                    logger.info(f"Successfully sent email to {len(recipients)} recipients using Redmine-compatible settings")
                    return True
                    
            except Exception as e:
                logger.error(f"Redmine-compatible SMTP failed: {e}")
                
                # Fallback: Try without STARTTLS for local MailPlus
                try:
                    logger.info("Trying fallback: Direct SMTP without STARTTLS")
                    
                    with smtplib.SMTP(self.settings.SMTP_HOST, 25, timeout=30) as server:
                        server.set_debuglevel(1)
                        
                        # Try without STARTTLS for local delivery
                        if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                            try:
                                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                            except Exception:
                                logger.info("Login not required for local SMTP")
                        
                        server.sendmail(
                            self.settings.EMAIL_FROM,
                            recipients,
                            message.as_string()
                        )
                        
                        logger.info("Fallback method succeeded")
                        return True
                        
                except Exception as e2:
                    logger.error(f"All SMTP methods failed. Primary error: {e}, Fallback error: {e2}")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to send email after trying all methods: {e}")
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
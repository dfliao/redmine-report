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
            
            # Try different SMTP approaches
            success = False
            
            # Method 1: TLS (Port 587)
            if not success and self.settings.SMTP_PORT == 587:
                try:
                    logger.info("Trying SMTP with STARTTLS (port 587)")
                    context = ssl.create_default_context()
                    
                    with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=30) as server:
                        server.set_debuglevel(1)  # Enable debug output
                        server.starttls(context=context)
                        
                        if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                            logger.info(f"Logging in with username: {self.settings.SMTP_USERNAME}")
                            server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                        
                        server.sendmail(
                            self.settings.EMAIL_FROM,
                            recipients,
                            message.as_string()
                        )
                        success = True
                        logger.info("STARTTLS method succeeded")
                        
                except Exception as e1:
                    logger.warning(f"STARTTLS method failed: {e1}")
            
            # Method 2: SSL (Port 465)  
            if not success:
                try:
                    logger.info("Trying SMTP with SSL (port 465)")
                    context = ssl.create_default_context()
                    
                    smtp_port = 465 if self.settings.SMTP_PORT == 587 else self.settings.SMTP_PORT
                    
                    with smtplib.SMTP_SSL(self.settings.SMTP_HOST, smtp_port, context=context, timeout=30) as server:
                        server.set_debuglevel(1)  # Enable debug output
                        
                        if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                            logger.info(f"Logging in with username: {self.settings.SMTP_USERNAME}")
                            server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                        
                        server.sendmail(
                            self.settings.EMAIL_FROM,
                            recipients,
                            message.as_string()
                        )
                        success = True
                        logger.info("SSL method succeeded")
                        
                except Exception as e2:
                    logger.warning(f"SSL method failed: {e2}")
            
            # Method 3: No encryption (Port 25)
            if not success:
                try:
                    logger.info("Trying SMTP without encryption (port 25)")
                    
                    with smtplib.SMTP(self.settings.SMTP_HOST, 25, timeout=30) as server:
                        server.set_debuglevel(1)  # Enable debug output
                        
                        # Try login if credentials provided
                        if hasattr(self.settings, 'SMTP_USERNAME') and self.settings.SMTP_USERNAME:
                            try:
                                server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                            except Exception:
                                logger.info("Login failed or not required for port 25")
                        
                        server.sendmail(
                            self.settings.EMAIL_FROM,
                            recipients,
                            message.as_string()
                        )
                        success = True
                        logger.info("No encryption method succeeded")
                        
                except Exception as e3:
                    logger.warning(f"No encryption method failed: {e3}")
            
            if success:
                logger.info(f"Successfully sent email to {len(recipients)} recipients")
                return True
            else:
                raise Exception("All SMTP methods failed")
            
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
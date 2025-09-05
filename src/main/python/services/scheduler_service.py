#!/usr/bin/env python3
"""
Scheduler Service

Service for scheduled report generation and sending.
"""

import logging
import asyncio
from datetime import datetime, time
from typing import Optional, List

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for scheduling automatic report generation and sending"""
    
    def __init__(self, report_generator, settings):
        self.report_generator = report_generator
        self.settings = settings
        self.running = False
        logger.info("Initialized Scheduler service")
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        logger.info("Scheduler service started")
    
    async def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler service stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.running
    
    def get_next_run_time(self) -> str:
        """Get next scheduled run time"""
        schedule_cron = getattr(self.settings, 'SCHEDULE_CRON', '0 8 * * 1')
        return f"Cron: {schedule_cron}"
    
    async def send_scheduled_reports(self):
        """Send all configured scheduled reports"""
        try:
            logger.info("Starting scheduled report sending")
            
            # Send Report 1 if enabled
            if getattr(self.settings, 'REPORT1_AUTO_SEND', True):  # Default enabled
                await self._send_report1()
            
            # Send Report 2 if enabled  
            if getattr(self.settings, 'REPORT2_AUTO_SEND', True):  # Default enabled
                await self._send_report2()
            
            # Send Report 3 if enabled
            if getattr(self.settings, 'REPORT3_AUTO_SEND', False):  # Weekly report
                await self._send_report3()
                
            logger.info("Completed scheduled report sending")
            
        except Exception as e:
            logger.error(f"Error in scheduled report sending: {e}")
            raise
    
    async def _send_report1(self):
        """Send Report 1 - Progress Statistics"""
        try:
            logger.info("Starting scheduled Report 1 generation")
            recipients = self._get_scheduled_recipients('REPORT1')
            result = await self.report_generator.generate_and_send_report1(recipients=recipients)
            
            if result.get('status') == 'success':
                logger.info(f"Scheduled Report 1 sent successfully to {len(result.get('recipients', []))} recipients")
            else:
                logger.error(f"Scheduled Report 1 failed: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"Error in scheduled Report 1: {e}")
    
    async def _send_report2(self):
        """Send Report 2 - Due Date Changes"""
        try:
            logger.info("Starting scheduled Report 2 generation")
            recipients = self._get_scheduled_recipients('REPORT2')
            result = await self.report_generator.generate_and_send_report2(recipients=recipients)
            
            if result.get('status') == 'success':
                logger.info(f"Scheduled Report 2 sent successfully to {len(result.get('recipients', []))} recipients")
            else:
                logger.error(f"Scheduled Report 2 failed: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"Error in scheduled Report 2: {e}")
    
    async def _send_report3(self):
        """Send Report 3 - Special Projects"""
        try:
            logger.info("Starting scheduled Report 3 generation")
            recipients = self._get_scheduled_recipients('REPORT3')
            result = await self.report_generator.generate_and_send_report3(recipients=recipients)
            
            if result.get('status') == 'success':
                logger.info(f"Scheduled Report 3 sent successfully to {len(result.get('recipients', []))} recipients")
            else:
                logger.error(f"Scheduled Report 3 failed: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"Error in scheduled Report 3: {e}")
    
    def _get_scheduled_recipients(self, report_type: str) -> Optional[List[str]]:
        """Get configured recipients for scheduled reports"""
        try:
            # Check for specific recipients in settings
            recipients_key = f"{report_type}_RECIPIENTS"
            recipients = getattr(self.settings, recipients_key, None)
            
            if recipients:
                if isinstance(recipients, str):
                    # Single email or comma-separated list
                    return [email.strip() for email in recipients.split(',')]
                elif isinstance(recipients, list):
                    return recipients
            
            # Fall back to default (all Redmine users)
            return None
            
        except Exception as e:
            logger.warning(f"Error getting scheduled recipients for {report_type}: {e}")
            return None
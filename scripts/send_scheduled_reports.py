#!/usr/bin/env python3
"""
Scheduled Report Sender

Script for sending scheduled reports via cron or manual execution.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main.python.core.settings import Settings
from src.main.python.services.redmine_service import RedmineService
from src.main.python.services.email_service import EmailService
from src.main.python.services.report_generator import ReportGenerator
from src.main.python.services.scheduler_service import SchedulerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/redmine_scheduled_reports.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to send scheduled reports"""
    try:
        logger.info("=== Starting scheduled report generation ===")
        
        # Initialize settings
        settings = Settings()
        logger.info("Settings initialized")
        
        # Initialize services
        redmine_service = RedmineService(settings)
        email_service = EmailService(settings)
        report_generator = ReportGenerator(settings, redmine_service, email_service)
        scheduler_service = SchedulerService(report_generator, settings)
        
        logger.info("Services initialized")
        
        # Send scheduled reports
        await scheduler_service.send_scheduled_reports()
        
        logger.info("=== Scheduled report generation completed ===")
        
    except Exception as e:
        logger.error(f"Error in scheduled report generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
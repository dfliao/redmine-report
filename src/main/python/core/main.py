#!/usr/bin/env python3
"""
Redmine Report Generator - Main Entry Point

This module provides the main entry point for the Redmine report generation system.
Supports web interface, API endpoints, and standalone execution.
"""

import asyncio
import logging
import sys
from typing import Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add the web app to the main app
from ..web.app import app as web_app
from ..services.report_generator import ReportGenerator  
from ..services.email_service import EmailService
from ..services.scheduler_service import SchedulerService
from ..utils.config import get_settings, validate_config, setup_logger

class ReportRequest(BaseModel):
    """Request model for manual report generation"""
    force: bool = False
    email_override: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    version: str

# Use the web app as the main app
app = web_app

# Global services
report_generator: Optional[ReportGenerator] = None
email_service: Optional[EmailService] = None  
scheduler_service: Optional[SchedulerService] = None
logger: Optional[logging.Logger] = None


async def initialize_services():
    """Initialize all services"""
    global report_generator, email_service, scheduler_service, logger
    
    # Setup logging
    logger = setup_logger(__name__)
    logger.info("Initializing Redmine Report Generator...")
    
    settings = get_settings()
    
    try:
        # Initialize services
        email_service = EmailService(settings)
        report_generator = ReportGenerator(settings, email_service)
        scheduler_service = SchedulerService(report_generator, settings)
        
        # Start scheduler
        await scheduler_service.start()
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    await initialize_services()


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event"""
    if scheduler_service:
        await scheduler_service.stop()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container monitoring"""
    return HealthResponse(status="healthy", version="1.0.0")


@app.post("/generate-report")
async def generate_report_endpoint(request: ReportRequest = ReportRequest()):
    """
    Generate and send report manually (for n8n integration)
    
    Args:
        request: Report generation request parameters
        
    Returns:
        Success message with report details
    """
    if not report_generator:
        raise HTTPException(status_code=503, detail="Report generator not initialized")
    
    try:
        logger.info(f"Manual report generation requested (force={request.force})")
        
        # Generate and send report
        result = await report_generator.generate_and_send_report(
            force=request.force,
            email_override=request.email_override
        )
        
        return {
            "success": True,
            "message": "Report generated and sent successfully",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get current service status"""
    return {
        "services": {
            "report_generator": "ready" if report_generator else "not_initialized",
            "email_service": "ready" if email_service else "not_initialized",
            "scheduler": "running" if scheduler_service and scheduler_service.is_running() else "stopped"
        },
        "next_scheduled_run": scheduler_service.get_next_run_time() if scheduler_service else None
    }


async def run_standalone():
    """Run standalone report generation"""
    await initialize_services()
    
    if report_generator:
        logger.info("Running standalone report generation...")
        try:
            result = await report_generator.generate_and_send_report()
            logger.info(f"Report generation completed: {result}")
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise
    else:
        logger.error("Failed to initialize report generator")


def main():
    """Main entry point"""
    try:
        # Validate configuration
        validate_config()
        settings = get_settings()
        
        if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
            # Run once and exit (useful for cron jobs)
            asyncio.run(run_standalone())
        else:
            # Run as web server with API (default for containers)
            uvicorn.run(
                "src.main.python.core.main:app",
                host=settings.API_HOST,
                port=settings.API_PORT,
                log_level=settings.LOG_LEVEL.lower(),
                reload=settings.DEBUG
            )
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
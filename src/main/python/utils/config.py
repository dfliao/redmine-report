#!/usr/bin/env python3
"""
Configuration Settings

Centralized configuration management for the Redmine Report system.
Uses environment variables with sensible defaults.
"""

import os
import logging
import sys
from typing import Optional
try:
    from pydantic import BaseSettings
except ImportError:
    from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Redmine Configuration
    REDMINE_URL: str = os.getenv('REDMINE_URL', 'http://localhost:3000')
    REDMINE_API_KEY: str = os.getenv('REDMINE_API_KEY', '')
    REDMINE_VERSION: str = os.getenv('REDMINE_VERSION', '6.0.6')
    REDMINE_TIMEOUT: int = int(os.getenv('REDMINE_TIMEOUT', '30'))
    REDMINE_VERIFY_SSL: bool = os.getenv('REDMINE_VERIFY_SSL', 'true').lower() == 'true'
    
    # Email Configuration (Redmine-compatible defaults)
    SMTP_HOST: str = os.getenv('SMTP_HOST', '192.168.0.222')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME: str = os.getenv('SMTP_USERNAME', 'GOPEAK@mail.gogopeaks.com')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '5w~IDW')
    EMAIL_FROM: str = os.getenv('EMAIL_FROM', 'GOPEAK@mail.gogopeaks.com')
    EMAIL_USE_TLS: bool = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
    EMAIL_USE_SSL: bool = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
    EMAIL_TIMEOUT: int = int(os.getenv('EMAIL_TIMEOUT', '60'))
    EMAIL_RETRY_ATTEMPTS: int = int(os.getenv('EMAIL_RETRY_ATTEMPTS', '3'))
    EMAIL_RETRY_DELAY: int = int(os.getenv('EMAIL_RETRY_DELAY', '5'))
    
    # Report Configuration
    REPORT_DAYS: int = int(os.getenv('REPORT_DAYS', '14'))
    TIMEZONE: str = os.getenv('TIMEZONE', 'Asia/Taipei')
    EMAIL_SUBJECT_TEMPLATE: str = os.getenv('EMAIL_SUBJECT_TEMPLATE', '【Redmine報表】{date} - 議題進度統計')
    EMAIL_CHARSET: str = os.getenv('EMAIL_CHARSET', 'utf-8')
    
    # API Configuration
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    API_PORT: int = int(os.getenv('API_PORT', '3003'))
    API_PREFIX: str = os.getenv('API_PREFIX', '/api/v1')
    
    # Scheduling Configuration
    SCHEDULE_CRON: str = os.getenv('SCHEDULE_CRON', '0 8 * * 1')  # Every Monday at 8:00 AM
    
    # Security Configuration
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'redmine-report-secret-key-2024')
    
    # Performance Configuration
    MAX_WORKERS: int = int(os.getenv('MAX_WORKERS', '2'))
    WORKER_TIMEOUT: int = int(os.getenv('WORKER_TIMEOUT', '300'))
    MEMORY_LIMIT: str = os.getenv('MEMORY_LIMIT', '256M')
    CPU_LIMIT: str = os.getenv('CPU_LIMIT', '0.8')
    
    # Caching Configuration (Optional)
    REDIS_URL: Optional[str] = os.getenv('REDIS_URL')
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '3600'))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global _settings
    _settings = None
    return get_settings()

# Validation functions
def validate_config() -> bool:
    """Validate critical configuration settings"""
    settings = get_settings()
    
    required_fields = [
        ('REDMINE_URL', settings.REDMINE_URL),
        ('REDMINE_API_KEY', settings.REDMINE_API_KEY),
        ('SMTP_HOST', settings.SMTP_HOST),
        ('EMAIL_FROM', settings.EMAIL_FROM),
    ]
    
    missing_fields = []
    for field_name, field_value in required_fields:
        if not field_value:
            missing_fields.append(field_name)
    
    if missing_fields:
        raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
    
    return True


def setup_logger(name: str) -> logging.Logger:
    """
    Setup structured logger with consistent formatting
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Create formatter
    if settings.DEBUG:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger
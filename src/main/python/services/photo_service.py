#!/usr/bin/env python3
"""
Photo Service

Service for managing Synology Photos and construction site photo scanning.
"""

import logging
import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import requests
from PIL import Image
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class PhotoService:
    """Service for Synology Photos and construction site photo management"""
    
    def __init__(self, settings):
        self.settings = settings
        
        # Photo settings
        self.photo_base_path = getattr(settings, 'PHOTO_BASE_PATH', '/volume1/photo/@@案場施工照片')
        self.synology_host = getattr(settings, 'SYNOLOGY_DSM_HOST', 'localhost')
        self.synology_port = getattr(settings, 'SYNOLOGY_DSM_PORT', 5001)
        self.photos_web_url = f"https://{self.synology_host}:{self.synology_port}/photo"
        
        # Date regex pattern for folder names: yyyy.mm.dd<<description>>
        self.date_pattern = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})(.*)')
        
        logger.info("Initialized Photo service")
    
    async def get_construction_photos(self, start_date: date = None, end_date: date = None, 
                                    project_filter: str = None) -> List[Dict]:
        """Get construction photos for specified date range and projects
        
        Args:
            start_date: Filter by construction date >= start_date
            end_date: Filter by construction date <= end_date  
            project_filter: Filter by project name (partial match)
        
        Returns:
            List of construction photo records
        """
        try:
            # Set default date range to past 14 days
            if not start_date:
                start_date = date.today() - timedelta(days=14)
            if not end_date:
                end_date = date.today()
                
            logger.info(f"Scanning construction photos from {start_date} to {end_date}, project: {project_filter}")
            
            # Scan the base photo directory
            if not os.path.exists(self.photo_base_path):
                logger.error(f"Photo base path does not exist: {self.photo_base_path}")
                return []
            
            construction_records = []
            
            # Get all project directories
            project_dirs = [d for d in os.listdir(self.photo_base_path) 
                          if os.path.isdir(os.path.join(self.photo_base_path, d))]
            
            for project_name in project_dirs:
                # Apply project filter
                if project_filter and project_filter.lower() not in project_name.lower():
                    continue
                    
                project_path = os.path.join(self.photo_base_path, project_name)
                
                # Get construction date folders for this project
                project_records = await self._scan_project_photos(
                    project_name, project_path, start_date, end_date
                )
                construction_records.extend(project_records)
            
            # Sort by project name, then by date (newest first)
            construction_records.sort(key=lambda x: (x['project_name'], x['construction_date']), reverse=True)
            
            logger.info(f"Found {len(construction_records)} construction photo records")
            return construction_records
            
        except Exception as e:
            logger.error(f"Error getting construction photos: {e}")
            raise
    
    async def _scan_project_photos(self, project_name: str, project_path: str, 
                                 start_date: date, end_date: date) -> List[Dict]:
        """Scan a single project directory for construction photos"""
        try:
            records = []
            
            if not os.path.exists(project_path):
                logger.warning(f"Project path does not exist: {project_path}")
                return records
            
            # Get all subdirectories (construction date folders)
            date_dirs = [d for d in os.listdir(project_path) 
                        if os.path.isdir(os.path.join(project_path, d))]
            
            # Generate expected dates in range for missing date detection
            current_date = start_date
            expected_dates = []
            while current_date <= end_date:
                expected_dates.append(current_date)
                current_date += timedelta(days=1)
            
            # Track found dates
            found_dates = set()
            
            for date_dir in date_dirs:
                # Parse date from folder name using regex
                match = self.date_pattern.match(date_dir)
                if not match:
                    continue
                    
                try:
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    construction_date = date(year, month, day)
                    description = match.group(4).strip('<>')  # Remove << >> if present
                    
                    # Check if date is in range
                    if start_date <= construction_date <= end_date:
                        found_dates.add(construction_date)
                        
                        # Get photos from this date folder
                        date_folder_path = os.path.join(project_path, date_dir)
                        photos = await self._get_folder_photos(date_folder_path)
                        
                        # Generate Synology Photos web URL
                        photos_url = await self._generate_photos_url(project_name, date_dir)
                        
                        record = {
                            'project_name': project_name,
                            'construction_date': construction_date.strftime('%Y-%m-%d'),
                            'construction_description': description or '施工作業',
                            'photos': photos,
                            'photo_count': len(photos),
                            'photos_web_url': photos_url,
                            'folder_name': date_dir
                        }
                        records.append(record)
                        
                except ValueError as e:
                    logger.warning(f"Invalid date in folder name {date_dir}: {e}")
                    continue
            
            # Add missing dates with "沒有" status
            for expected_date in expected_dates:
                if expected_date not in found_dates:
                    record = {
                        'project_name': project_name,
                        'construction_date': expected_date.strftime('%Y-%m-%d'),
                        'construction_description': '沒有',
                        'photos': [],
                        'photo_count': 0,
                        'photos_web_url': None,
                        'folder_name': None
                    }
                    records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Error scanning project {project_name}: {e}")
            return []
    
    async def _get_folder_photos(self, folder_path: str, max_photos: int = 3) -> List[Dict]:
        """Get photos from a construction date folder"""
        try:
            photos = []
            
            if not os.path.exists(folder_path):
                return photos
            
            # Supported image extensions
            image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.bmp'}
            
            # Get all image files
            image_files = []
            for file in os.listdir(folder_path):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(file)
            
            # Sort files by name and take first N photos
            image_files.sort()
            selected_files = image_files[:max_photos]
            
            for filename in selected_files:
                file_path = os.path.join(folder_path, filename)
                
                try:
                    # Get file info
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    
                    # Generate thumbnail
                    thumbnail_data = await self._generate_thumbnail(file_path)
                    
                    photo_info = {
                        'filename': filename,
                        'file_path': file_path,
                        'file_size': file_size,
                        'modified_time': modified_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'thumbnail_base64': thumbnail_data
                    }
                    photos.append(photo_info)
                    
                except Exception as e:
                    logger.warning(f"Error processing photo {file_path}: {e}")
                    continue
            
            return photos
            
        except Exception as e:
            logger.error(f"Error getting folder photos from {folder_path}: {e}")
            return []
    
    async def _generate_thumbnail(self, image_path: str, size: tuple = (200, 150)) -> str:
        """Generate base64 thumbnail for image"""
        try:
            # For HEIC files, we might need special handling
            if image_path.lower().endswith(('.heic', '.heif')):
                # Return a placeholder for HEIC files since PIL might not support them
                return self._get_placeholder_thumbnail()
            
            # Open and resize image
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save to bytes
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                
                # Encode to base64
                thumbnail_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{thumbnail_data}"
                
        except Exception as e:
            logger.warning(f"Error generating thumbnail for {image_path}: {e}")
            return self._get_placeholder_thumbnail()
    
    def _get_placeholder_thumbnail(self) -> str:
        """Get placeholder thumbnail for unsupported image formats"""
        # Simple 1x1 transparent image
        placeholder = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        return placeholder
    
    async def _generate_photos_url(self, project_name: str, date_folder: str) -> str:
        """Generate Synology Photos web URL for the folder"""
        try:
            # Base URL pattern: https://hostname:5001/photo/#/shared_space/folder/ID
            # For now, we'll generate a basic URL - actual folder ID would need API call
            # This is a simplified version that constructs a path-based URL
            
            encoded_project = requests.utils.quote(project_name)
            encoded_folder = requests.utils.quote(date_folder)
            
            # Construct URL (simplified - actual implementation would need folder ID from API)
            photos_url = f"{self.photos_web_url}/#/shared_space/folder_path/@@案場施工照片/{encoded_project}/{encoded_folder}"
            
            return photos_url
            
        except Exception as e:
            logger.warning(f"Error generating photos URL: {e}")
            return f"{self.photos_web_url}/#/shared_space"
    
    async def get_available_projects(self) -> List[Dict]:
        """Get list of available construction projects"""
        try:
            if not os.path.exists(self.photo_base_path):
                logger.error(f"Photo base path does not exist: {self.photo_base_path}")
                return []
            
            projects = []
            project_dirs = [d for d in os.listdir(self.photo_base_path) 
                          if os.path.isdir(os.path.join(self.photo_base_path, d))]
            
            for project_dir in project_dirs:
                project_path = os.path.join(self.photo_base_path, project_dir)
                
                # Count construction date folders
                date_folders = [d for d in os.listdir(project_path) 
                              if os.path.isdir(os.path.join(project_path, d)) and self.date_pattern.match(d)]
                
                projects.append({
                    'name': project_dir,
                    'folder_count': len(date_folders)
                })
            
            projects.sort(key=lambda x: x['name'])
            return projects
            
        except Exception as e:
            logger.error(f"Error getting available projects: {e}")
            return []
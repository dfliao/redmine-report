#!/usr/bin/env python3
"""
Redmine Service

Service class for interacting with Redmine API to fetch issue data,
statistics, and journal entries for due date change tracking.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from redminelib import Redmine
try:
    from redminelib.exceptions import RedmineError
except ImportError:
    # Newer versions use different exception names
    from redminelib.exceptions import BaseRedmineError as RedmineError

logger = logging.getLogger(__name__)

class RedmineService:
    """Service for Redmine API operations"""
    
    def __init__(self, settings):
        self.settings = settings
        self.redmine = Redmine(
            settings.REDMINE_URL,
            key=settings.REDMINE_API_KEY,
            timeout=getattr(settings, 'REDMINE_TIMEOUT', 30)
        )
        logger.info(f"Initialized Redmine service for {settings.REDMINE_URL}")
    
    async def get_issue_statistics(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get issue count statistics by assignee and status
        For Report 1 - Table 1
        """
        try:
            # Get issues within date range that are in progress
            issues = self.redmine.issue.filter(
                updated_on=f">={start_date.strftime('%Y-%m-%d')}",
                created_on=f"<={end_date.strftime('%Y-%m-%d')}",
                status_id='*',  # All statuses
                include=['journals']
            )
            
            # Process statistics by role, assignee and status
            stats = {}
            
            for issue in issues:
                assignee = issue.assigned_to.name if hasattr(issue, 'assigned_to') else '未分派'
                status = issue.status.name if hasattr(issue, 'status') else '未知狀態'
                
                # Get user role/group - for now use a simple mapping or custom field
                # This can be enhanced to get actual Redmine user groups/roles
                role = self._get_user_role(issue.assigned_to if hasattr(issue, 'assigned_to') else None)
                
                key = (role, assignee)
                if key not in stats:
                    stats[key] = {}
                
                if status not in stats[key]:
                    stats[key][status] = 0
                
                stats[key][status] += 1
            
            # Convert to list format for frontend
            result = []
            for (role, assignee), statuses in stats.items():
                row = {
                    'role': role,
                    'assignee': assignee
                }
                row.update(statuses)
                result.append(row)
            
            # Sort by role, then by assignee
            result.sort(key=lambda x: (x['role'], x['assignee']))
            
            logger.info(f"Retrieved statistics for {len(result)} assignees")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_issue_statistics: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_issue_statistics: {e}")
            raise
    
    async def get_issue_list(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get detailed issue list for issues due within the date range
        For Report 1 - Table 2
        """
        try:
            # Get issues with due dates within the range
            issues = self.redmine.issue.filter(
                due_date=f"><{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}",
                status_id='*',
                sort='due_date:asc',
                include=['journals']
            )
            
            result = []
            for issue in issues:
                result.append({
                    'project': issue.project.name if hasattr(issue, 'project') else '',
                    'priority': issue.priority.name if hasattr(issue, 'priority') else '',
                    'tracker': issue.tracker.name if hasattr(issue, 'tracker') else '',
                    'assigned_to': issue.assigned_to.name if hasattr(issue, 'assigned_to') else '未分派',
                    'status': issue.status.name if hasattr(issue, 'status') else '',
                    'subject': issue.subject,
                    'due_date': issue.due_date.strftime('%Y-%m-%d') if hasattr(issue, 'due_date') and issue.due_date else '',
                    'start_date': issue.start_date.strftime('%Y-%m-%d') if hasattr(issue, 'start_date') and issue.start_date else '',
                    'updated_on': issue.updated_on.strftime('%Y-%m-%d %H:%M') if hasattr(issue, 'updated_on') else ''
                })
            
            # Sort by project, priority, tracker, assigned_to, status
            result.sort(key=lambda x: (
                x['project'], 
                x['priority'], 
                x['tracker'], 
                x['assigned_to'], 
                x['status']
            ))
            
            logger.info(f"Retrieved {len(result)} issues for detailed list")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_issue_list: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_issue_list: {e}")
            raise
    
    async def get_due_date_changes(self, status_filter: str, update_date: date) -> List[Dict]:
        """
        Get issues where due date was changed on the specified date
        For Report 2 - Due date change tracking
        """
        try:
            # Get issues updated on the specified date with open status
            date_str = update_date.strftime('%Y-%m-%d')
            
            # First get all issues updated on the target date
            issues = self.redmine.issue.filter(
                updated_on=date_str,
                status_id='o' if status_filter == 'open' else '*',
                include=['journals']
            )
            
            result = []
            
            for issue in issues:
                # Check journals for due date changes
                due_date_changes = self._extract_due_date_changes(issue, update_date)
                
                if due_date_changes:
                    for change in due_date_changes:
                        # Calculate date adjustment
                        days_adjustment = self._calculate_days_adjustment(
                            change['old_date'], 
                            change['new_date']
                        )
                        
                        result.append({
                            'project': issue.project.name if hasattr(issue, 'project') else '',
                            'priority': issue.priority.name if hasattr(issue, 'priority') else '',
                            'subject': issue.subject,
                            'modifier': change['user'],
                            'assigned_to': issue.assigned_to.name if hasattr(issue, 'assigned_to') else '未分派',
                            'new_due_date': change['new_date'],
                            'old_due_date': change['old_date'],
                            'days_adjustment': days_adjustment,
                            'change_date': change['change_date']
                        })
            
            # Sort by project, adjustment days desc, priority, assigned_to
            def sort_key(x):
                # Extract numeric value from days_adjustment for proper sorting
                days_str = x['days_adjustment']
                if days_str == "N/A":
                    days_num = 0  # Treat N/A as 0 for sorting
                else:
                    # Extract number from "+5天" or "-3天" format
                    days_num = int(days_str.replace('天', '').replace('+', ''))
                
                return (
                    x['project'],
                    -days_num,  # Negative for descending order
                    x['priority'],
                    x['assigned_to']
                )
            
            result.sort(key=sort_key)
            
            logger.info(f"Found {len(result)} due date changes on {date_str}")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_due_date_changes: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_due_date_changes: {e}")
            raise
    
    def _extract_due_date_changes(self, issue, target_date: date) -> List[Dict]:
        """Extract due date changes from issue journals"""
        changes = []
        
        if not hasattr(issue, 'journals'):
            return changes
        
        for journal in issue.journals:
            # Check if journal date matches target date
            journal_date = journal.created_on.date()
            if journal_date != target_date:
                continue
            
            # Check if this journal contains due date changes
            if hasattr(journal, 'details'):
                for detail in journal.details:
                    # Handle both dict and object formats for detail
                    if isinstance(detail, dict):
                        # python-redmine 2.5.0+ returns dict format
                        field_name = detail.get('name', '')
                        old_value = detail.get('old_value', '')
                        new_value = detail.get('new_value', '')
                        property_type = detail.get('property', '')
                    else:
                        # Legacy object format
                        field_name = getattr(detail, 'name', '')
                        old_value = getattr(detail, 'old_value', '')
                        new_value = getattr(detail, 'new_value', '')
                        property_type = getattr(detail, 'property', '')
                    
                    # Check if this is a due_date change for attribute properties
                    if property_type == 'attr' and field_name == 'due_date':
                        changes.append({
                            'user': journal.user.name if hasattr(journal, 'user') else 'Unknown',
                            'old_date': old_value or '',
                            'new_date': new_value or '',
                            'change_date': journal.created_on.strftime('%Y-%m-%d %H:%M')
                        })
        
        return changes
    
    def _get_user_role(self, user) -> str:
        """
        Get user role/group name
        For now, use a simple mapping based on user name or can be enhanced
        to fetch actual Redmine user groups/roles via API
        """
        if not user:
            return '未分派'
        
        try:
            # Try to get user groups if available
            if hasattr(user, 'groups'):
                # If user has groups, return the first group name
                if user.groups:
                    return user.groups[0].name if hasattr(user.groups[0], 'name') else '一般使用者'
            
            # Simple role mapping based on user name patterns (can be customized)
            username = user.name if hasattr(user, 'name') else str(user)
            
            # You can customize these role mappings based on your organization
            if 'manager' in username.lower() or '經理' in username or '主管' in username:
                return '管理階層'
            elif 'engineer' in username.lower() or '工程師' in username:
                return '工程師'
            elif 'admin' in username.lower() or '管理員' in username:
                return '系統管理員'
            else:
                return '一般使用者'
                
        except Exception:
            return '一般使用者'
    
    def _calculate_days_adjustment(self, old_date_str: str, new_date_str: str) -> str:
        """Calculate the number of days adjustment between old and new due dates"""
        try:
            if not old_date_str or not new_date_str:
                return "N/A"
            
            old_date = datetime.strptime(old_date_str, '%Y-%m-%d').date()
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            
            diff = (new_date - old_date).days
            
            if diff > 0:
                return f"+{diff}天"
            elif diff < 0:
                return f"{diff}天"  # Already has minus sign
            else:
                return "0天"
                
        except ValueError:
            return "N/A"
    
    async def get_total_issue_count(self) -> int:
        """Get total number of issues"""
        try:
            issues = self.redmine.issue.filter(status_id='*', limit=1)
            return issues.total_count if hasattr(issues, 'total_count') else 0
        except Exception as e:
            logger.error(f"Error getting total issue count: {e}")
            return 0
    
    async def get_open_issue_count(self) -> int:
        """Get count of open issues"""
        try:
            issues = self.redmine.issue.filter(status_id='o', limit=1)
            return issues.total_count if hasattr(issues, 'total_count') else 0
        except Exception as e:
            logger.error(f"Error getting open issue count: {e}")
            return 0
    
    async def get_today_update_count(self) -> int:
        """Get count of issues updated today"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            issues = self.redmine.issue.filter(updated_on=today, limit=1)
            return issues.total_count if hasattr(issues, 'total_count') else 0
        except Exception as e:
            logger.error(f"Error getting today update count: {e}")
            return 0
    
    async def get_issue_statuses(self) -> List[Dict]:
        """Get available issue statuses"""
        try:
            statuses = self.redmine.issue_status.all()
            return [
                {
                    'id': status.id,
                    'name': status.name,
                    'is_closed': getattr(status, 'is_closed', False)
                }
                for status in statuses
            ]
        except Exception as e:
            logger.error(f"Error getting issue statuses: {e}")
            return []
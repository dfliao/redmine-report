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
        
        # Define status order and aggregation logic
        self.status_order = [
            '擬定中', '執行中', '簽核中', '已完成(結案)', 
            '撤回', '暫停', '取消'
        ]
        
        # Statuses that are aggregated into "簽核中"
        self.approval_statuses = ['簽核中', '審查中', '已審核', '已覆審(工廠)', '已覆審']
        
        # Special project configuration for Report 3
        self.special_project_id = 'a55700'  # 專項用 project ID
        self.special_project_ids = set()  # Will be populated with parent + sub-project IDs
        
        # Initialize special project IDs (parent + all sub-projects)
        self._initialize_special_project_ids()
        
        logger.info(f"Initialized Redmine service for {settings.REDMINE_URL}")
    
    def _initialize_special_project_ids(self):
        """Initialize special project IDs by querying Redmine for parent and sub-projects"""
        try:
            # Add the main special project ID
            self.special_project_ids.add(self.special_project_id)
            
            # Query all projects to find sub-projects
            all_projects = self.redmine.project.all()
            
            for project in all_projects:
                # Check if this project is a sub-project of our special project
                if hasattr(project, 'parent') and project.parent:
                    parent_id = str(getattr(project.parent, 'id', ''))
                    if parent_id == self.special_project_id:
                        # This is a direct sub-project
                        self.special_project_ids.add(str(project.id))
                        logger.info(f"Found sub-project: {project.name} (ID: {project.id})")
                
                # Also check for nested sub-projects (sub-projects of sub-projects)
                project_id = str(project.id)
                if project_id in self.special_project_ids and hasattr(project, 'parent'):
                    # This project is already in our special projects, check for its children
                    for child_project in all_projects:
                        if hasattr(child_project, 'parent') and child_project.parent:
                            child_parent_id = str(getattr(child_project.parent, 'id', ''))
                            if child_parent_id == project_id:
                                self.special_project_ids.add(str(child_project.id))
                                logger.info(f"Found nested sub-project: {child_project.name} (ID: {child_project.id})")
            
            logger.info(f"Special project IDs initialized: {self.special_project_ids}")
            
        except Exception as e:
            logger.error(f"Error initializing special project IDs: {e}")
            # Fallback to just the main project
            self.special_project_ids = {self.special_project_id}
    
    def _should_exclude_issue(self, issue, for_special_project=False) -> bool:
        """Check if an issue should be excluded based on project"""
        try:
            if hasattr(issue, 'project'):
                project_id = str(getattr(issue.project, 'id', ''))
                
                if for_special_project:
                    # For special project reports (report 3), include ONLY special project family
                    if project_id in self.special_project_ids:
                        return False  # Don't exclude - include this
                    return True  # Exclude - not in special project family
                else:
                    # For regular reports (1 & 2), exclude special project family
                    if project_id in self.special_project_ids:
                        return True  # Exclude this
                            
            return False
        except Exception as e:
            logger.warning(f"Error checking project exclusion for issue: {e}")
            return False
    
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
                # Skip excluded projects
                if self._should_exclude_issue(issue):
                    continue
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
            
            # Convert to list format for frontend with status aggregation
            result = []
            for (role, assignee), statuses in stats.items():
                row = {
                    'role': role,
                    'assignee': assignee
                }
                
                # Initialize all status columns with 0
                for status in self.status_order:
                    row[status] = 0
                
                # Calculate "簽核中" aggregation
                approval_count = 0
                for status_name, count in statuses.items():
                    if status_name in self.approval_statuses:
                        approval_count += count
                        # Don't add individual approval statuses to display, only the aggregated one
                    elif status_name in self.status_order:
                        row[status_name] = count
                
                # Set the aggregated "簽核中" count
                row['簽核中'] = approval_count
                
                result.append(row)
            
            # Sort by role, then by assignee
            result.sort(key=lambda x: (x['role'], x['assignee']))
            
            logger.info(f"Retrieved statistics for {len(result)} assignees with status aggregation")
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
                # Skip excluded projects
                if self._should_exclude_issue(issue):
                    continue
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
                # Skip excluded projects
                if self._should_exclude_issue(issue):
                    continue
                    
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
            # Force evaluation by converting to list first, then get total_count
            issues = self.redmine.issue.filter(limit=1)
            
            # Force evaluation to get total_count
            try:
                # This forces the query to execute
                list(issues)
                total = getattr(issues, 'total_count', 0)
                logger.info(f"Total issues count: {total}")
                return total
            except Exception as e:
                logger.warning(f"total_count method failed: {e}, trying manual count")
                # Manual count fallback
                all_issues = self.redmine.issue.all()
                count = len(list(all_issues))
                logger.info(f"Manual count total issues: {count}")
                return count
                
        except Exception as e:
            logger.error(f"Error getting total issue count: {e}")
            return 0
    
    async def get_open_issue_count(self) -> int:
        """Get count of open issues"""
        try:
            # Try using the 'open' status first
            try:
                issues = self.redmine.issue.filter(status_id='o', limit=1)
                # Force evaluation
                list(issues)
                total = getattr(issues, 'total_count', 0)
                logger.info(f"Open issues count (method 1): {total}")
                return total
            except Exception as e1:
                logger.warning(f"Open status 'o' failed: {e1}, trying status IDs")
                
                # Get all open statuses and try specific IDs
                try:
                    statuses = self.redmine.issue_status.all()
                    open_status_ids = [str(s.id) for s in statuses if not getattr(s, 'is_closed', False)]
                    
                    if open_status_ids:
                        issues = self.redmine.issue.filter(status_id='|'.join(open_status_ids), limit=1)
                        list(issues)
                        total = getattr(issues, 'total_count', 0)
                        logger.info(f"Open issues count (method 2): {total}")
                        return total
                except Exception as e2:
                    logger.warning(f"Status ID method failed: {e2}, trying manual count")
                    
                    # Manual count fallback
                    try:
                        statuses = self.redmine.issue_status.all()
                        open_status_ids = [s.id for s in statuses if not getattr(s, 'is_closed', False)]
                        
                        if open_status_ids:
                            issues = self.redmine.issue.filter(status_id='|'.join(map(str, open_status_ids)))
                            count = len(list(issues))
                            logger.info(f"Manual count open issues: {count}")
                            return count
                    except Exception as e3:
                        logger.error(f"All open count methods failed: {e3}")
                        
            return 0
        except Exception as e:
            logger.error(f"Error getting open issue count: {e}")
            return 0
    
    async def get_today_update_count(self) -> int:
        """Get count of issues updated today"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Try different date formats for updated_on filter
            try:
                issues = self.redmine.issue.filter(updated_on=f'>={today}', limit=1)
                # Force evaluation
                list(issues)
                total = getattr(issues, 'total_count', 0)
                logger.info(f"Today updated issues count (method 1): {total}")
                return total
            except Exception as e1:
                logger.warning(f"Date filter '>=' failed: {e1}, trying exact date")
                
                try:
                    # Try exact date match
                    issues = self.redmine.issue.filter(updated_on=today, limit=1)
                    list(issues)
                    total = getattr(issues, 'total_count', 0)
                    logger.info(f"Today updated issues count (method 2): {total}")
                    return total
                except Exception as e2:
                    logger.warning(f"Exact date filter failed: {e2}, trying manual count")
                    
                    # Manual count fallback
                    try:
                        issues = self.redmine.issue.filter(updated_on=f'>={today}')
                        count = len(list(issues))
                        logger.info(f"Manual count today updated issues: {count}")
                        return count
                    except Exception as e3:
                        logger.error(f"All today update methods failed: {e3}")
                        
            return 0
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
    
    async def get_users(self) -> List[Dict]:
        """Get all active users in Redmine"""
        try:
            # Try different approaches to get users
            users_list = []
            
            # Method 1: Try to get users with status filter
            try:
                users = self.redmine.user.filter(status=1, limit=100)
                users_list = list(users)
                logger.info(f"Successfully loaded {len(users_list)} users with status filter")
            except Exception as e1:
                logger.warning(f"Method 1 failed: {e1}")
                
                # Method 2: Try without status filter  
                try:
                    users = self.redmine.user.all()
                    users_list = list(users)[:50]  # Limit to first 50 users
                    logger.info(f"Successfully loaded {len(users_list)} users without status filter")
                except Exception as e2:
                    logger.warning(f"Method 2 failed: {e2}")
                    
                    # Method 3: Return fallback with admin email
                    logger.error(f"All user loading methods failed, using fallback")
                    return [{
                        'id': 1,
                        'name': 'System Admin',
                        'login': 'admin',
                        'email': 'admin@example.com',
                        'firstname': 'Admin',
                        'lastname': 'User'
                    }]
            
            # Process the users we got
            result = []
            for user in users_list:
                try:
                    # Handle different user object formats
                    name = getattr(user, 'name', None)
                    if not name:
                        firstname = getattr(user, 'firstname', '')
                        lastname = getattr(user, 'lastname', '')
                        name = f"{firstname} {lastname}".strip()
                    
                    email = getattr(user, 'mail', '') or getattr(user, 'email', '')
                    
                    # Only include users with valid email
                    if email and '@' in email:
                        result.append({
                            'id': getattr(user, 'id', 0),
                            'name': name or 'Unknown User',
                            'login': getattr(user, 'login', ''),
                            'email': email,
                            'firstname': getattr(user, 'firstname', ''),
                            'lastname': getattr(user, 'lastname', '')
                        })
                except Exception as e:
                    logger.warning(f"Error processing user {user}: {e}")
                    continue
            
            logger.info(f"Processed {len(result)} users with valid emails")
            return result
            
        except Exception as e:
            logger.error(f"Critical error getting users: {e}")
            # Return a fallback list with admin email
            return [{
                'id': 1,
                'name': 'Test User',
                'login': 'test',
                'email': 'test@example.com',
                'firstname': 'Test',
                'lastname': 'User'
            }]
    
    async def authenticate_admin(self, username: str, password: str) -> bool:
        """
        Authenticate user with Redmine and check admin privileges
        
        Args:
            username: Redmine username
            password: Redmine password
            
        Returns:
            True if user is authenticated and has admin privileges
        """
        try:
            # Create a temporary Redmine instance with username/password
            temp_redmine = Redmine(
                self.settings.REDMINE_URL,
                username=username,
                password=password,
                timeout=getattr(self.settings, 'REDMINE_TIMEOUT', 30)
            )
            
            # Try to access user info to verify credentials
            try:
                current_user = temp_redmine.user.get('current')
                logger.info(f"User {username} authenticated successfully")
                
                # Check if user has admin privileges
                # Method 1: Check if user can access all projects
                try:
                    projects = temp_redmine.project.all()
                    projects_list = list(projects[:5])  # Test access to first 5 projects
                    logger.info(f"User {username} can access projects - likely admin")
                    return True
                except Exception as e:
                    logger.warning(f"User {username} cannot access all projects: {e}")
                
                # Method 2: Check if user can access user management
                try:
                    users = temp_redmine.user.all()
                    users_list = list(users[:5])  # Test access to first 5 users
                    logger.info(f"User {username} can access users - admin confirmed")
                    return True
                except Exception as e:
                    logger.warning(f"User {username} cannot access user management: {e}")
                
                # Method 3: Check user's admin attribute if available
                try:
                    admin_status = getattr(current_user, 'admin', False)
                    if admin_status:
                        logger.info(f"User {username} has admin flag set")
                        return True
                except Exception as e:
                    logger.warning(f"Cannot check admin flag for {username}: {e}")
                
                # If we reach here, user is authenticated but not admin
                logger.warning(f"User {username} authenticated but no admin privileges found")
                return False
                
            except RedmineError as e:
                logger.error(f"Redmine authentication failed for {username}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}")
            return False
    
    async def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticate user with Redmine credentials (without requiring admin privileges)
        
        Args:
            username: Redmine username
            password: Redmine password
            
        Returns:
            True if user credentials are valid
        """
        try:
            # Create a temporary Redmine instance with username/password
            temp_redmine = Redmine(
                self.settings.REDMINE_URL,
                username=username,
                password=password,
                timeout=getattr(self.settings, 'REDMINE_TIMEOUT', 30)
            )
            
            # Try to access user info to verify credentials
            try:
                current_user = temp_redmine.user.get('current')
                logger.info(f"User {username} authenticated successfully")
                return True
                
            except RedmineError as e:
                logger.error(f"Redmine authentication failed for {username}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error for {username}: {e}")
            return False
    
    def get_status_order(self) -> List[str]:
        """Get the ordered list of statuses for report display"""
        return self.status_order.copy()
    
    def get_status_aggregation_note(self) -> str:
        """Get the note explaining status aggregation logic"""
        return "註：簽核中為狀態「簽核中、審查中、已審核、已覆審(工廠)、已覆審」的加總"
    
    async def get_special_project_statistics(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get issue count statistics for special projects (專項用) only
        For Report 3
        """
        try:
            # Get issues within date range that are in special projects
            issues = self.redmine.issue.filter(
                updated_on=f">={start_date.strftime('%Y-%m-%d')}",
                created_on=f"<={end_date.strftime('%Y-%m-%d')}",
                status_id='*',  # All statuses
                include=['journals']
            )
            
            # Process statistics by role, assignee and status for special projects only
            stats = {}
            
            for issue in issues:
                # Include only special projects (專項用)
                if self._should_exclude_issue(issue, for_special_project=True):
                    continue
                    
                assignee = issue.assigned_to.name if hasattr(issue, 'assigned_to') else '未分派'
                status = issue.status.name if hasattr(issue, 'status') else '未知狀態'
                
                # Get user role/group
                role = self._get_user_role(issue.assigned_to if hasattr(issue, 'assigned_to') else None)
                
                key = (role, assignee)
                if key not in stats:
                    stats[key] = {}
                
                if status not in stats[key]:
                    stats[key][status] = 0
                
                stats[key][status] += 1
            
            # Convert to list format for frontend with status aggregation
            result = []
            for (role, assignee), statuses in stats.items():
                row = {
                    'role': role,
                    'assignee': assignee
                }
                
                # Initialize all status columns with 0
                for status in self.status_order:
                    row[status] = 0
                
                # Calculate "簽核中" aggregation
                approval_count = 0
                for status_name, count in statuses.items():
                    if status_name in self.approval_statuses:
                        approval_count += count
                        # Don't add individual approval statuses to display, only the aggregated one
                    elif status_name in self.status_order:
                        row[status_name] = count
                
                # Set the aggregated "簽核中" count
                row['簽核中'] = approval_count
                
                result.append(row)
            
            # Sort by role, then by assignee
            result.sort(key=lambda x: (x['role'], x['assignee']))
            
            logger.info(f"Retrieved special project statistics for {len(result)} assignees")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_special_project_statistics: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_special_project_statistics: {e}")
            raise
    
    async def get_special_project_issue_list(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Get detailed issue list for special projects (專項用) only
        For Report 3
        """
        try:
            # Get issues with due dates within the range for special projects
            issues = self.redmine.issue.filter(
                due_date=f"><{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}",
                status_id='*',
                sort='due_date:asc',
                include=['journals']
            )
            
            result = []
            for issue in issues:
                # Include only special projects (專項用)
                if self._should_exclude_issue(issue, for_special_project=True):
                    continue
                    
                result.append({
                    'project': issue.project.name if hasattr(issue, 'project') else '',
                    'priority': issue.priority.name if hasattr(issue, 'priority') else '',
                    'tracker': issue.tracker.name if hasattr(issue, 'tracker') else '',
                    'assigned_to': issue.assigned_to.name if hasattr(issue, 'assigned_to') else '未分派',
                    'status': issue.status.name if hasattr(issue, 'status') else '',
                    'subject': issue.subject if hasattr(issue, 'subject') else '',
                    'due_date': issue.due_date.strftime('%Y-%m-%d') if hasattr(issue, 'due_date') and issue.due_date else '',
                    'start_date': issue.start_date.strftime('%Y-%m-%d') if hasattr(issue, 'start_date') and issue.start_date else '',
                    'updated_on': issue.updated_on.strftime('%Y-%m-%d %H:%M') if hasattr(issue, 'updated_on') else ''
                })
            
            # Sort by project, priority, tracker, assignee, status
            result.sort(key=lambda x: (
                x['project'], 
                x['priority'], 
                x['tracker'],
                x['assigned_to'],
                x['status']
            ))
            
            logger.info(f"Retrieved {len(result)} special project issues")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_special_project_issue_list: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_special_project_issue_list: {e}")
            raise
    
    async def get_gantt_chart_data(self, start_date: date = None, end_date: date = None, 
                                 project_filter: str = None, tracker_filter: str = None,
                                 status_filter: List[str] = None) -> List[Dict]:
        """Get Gantt chart data for construction/installation projects with filtering options
        
        Args:
            start_date: Filter by due date >= start_date
            end_date: Filter by due date <= end_date  
            project_filter: Filter by project name (partial match)
            tracker_filter: Filter by tracker name (partial match)
            status_filter: Filter by status names (exact match list)
        """
        try:
            logger.info(f"Getting Gantt chart data with filters - Date: {start_date} to {end_date}, Project: {project_filter}, Tracker: {tracker_filter}, Status: {status_filter}")
            
            # Get all open issues excluding 專項用 projects
            issues = self.redmine.issue.filter(
                status_id='open'
            )
            
            result = []
            for issue in issues:
                # Exclude 專項用 projects (normal exclusion logic)
                if self._should_exclude_issue(issue):
                    continue
                
                # Apply project filter
                if project_filter:
                    project_name = getattr(issue.project, 'name', '') if hasattr(issue, 'project') else ''
                    if project_filter.lower() not in project_name.lower():
                        continue
                
                # Apply tracker filter  
                if tracker_filter:
                    tracker_name = getattr(issue.tracker, 'name', '') if hasattr(issue, 'tracker') else ''
                    if tracker_filter.lower() not in tracker_name.lower():
                        continue
                
                # Apply status filter
                if status_filter:
                    issue_status = getattr(issue.status, 'name', '') if hasattr(issue, 'status') else ''
                    if issue_status not in status_filter:
                        continue
                
                # Apply date filter (based on due_date)
                if hasattr(issue, 'due_date') and issue.due_date:
                    issue_due_date = issue.due_date
                    
                    if start_date and issue_due_date < start_date:
                        continue
                        
                    if end_date and issue_due_date > end_date:
                        continue
                
                # Format issue data for Gantt chart display
                gantt_data = self._format_gantt_issue_data(issue)
                if gantt_data:
                    result.append(gantt_data)
            
            # Sort by project, then by start_date
            result.sort(key=lambda x: (x.get('project', ''), x.get('start_date', '')))
            
            logger.info(f"Found {len(result)} issues for Gantt chart after filtering")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_gantt_chart_data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_gantt_chart_data: {e}")
            raise
    
    def _format_gantt_issue_data(self, issue) -> dict:
        """Format issue data specifically for Gantt chart display"""
        try:
            # Skip issues without both start_date and due_date
            if not (hasattr(issue, 'start_date') and hasattr(issue, 'due_date') and 
                   issue.start_date and issue.due_date):
                return None
            
            return {
                'id': issue.id,
                'project': getattr(issue.project, 'name', '') if hasattr(issue, 'project') else '',
                'tracker': getattr(issue.tracker, 'name', '') if hasattr(issue, 'tracker') else '',
                'subject': getattr(issue, 'subject', ''),
                'status': getattr(issue.status, 'name', '') if hasattr(issue, 'status') else '',
                'priority': getattr(issue.priority, 'name', '') if hasattr(issue, 'priority') else '',
                'assigned_to': getattr(issue.assigned_to, 'name', '') if hasattr(issue, 'assigned_to') else '未分派',
                'start_date': str(issue.start_date) if issue.start_date else '',
                'due_date': str(issue.due_date) if issue.due_date else '',
                'done_ratio': getattr(issue, 'done_ratio', 0),
                'updated_on': issue.updated_on.strftime('%Y-%m-%d') if hasattr(issue, 'updated_on') and issue.updated_on else ''
            }
        except Exception as e:
            logger.warning(f"Error formatting Gantt issue data for issue {getattr(issue, 'id', 'unknown')}: {e}")
            return None
    
    async def get_available_projects(self) -> List[Dict]:
        """Get list of available projects (excluding 專項用) for filtering"""
        try:
            projects = self.redmine.project.all()
            result = []
            
            for project in projects:
                project_name = getattr(project, 'name', '')
                project_id = str(getattr(project, 'id', ''))
                
                # Exclude special projects (專項用 and its sub-projects) from gantt chart project list
                if project_id in self.special_project_ids:
                    continue
                    
                result.append({
                    'id': getattr(project, 'id', ''),
                    'name': project_name,
                    'identifier': getattr(project, 'identifier', '')
                })
            
            # Sort by name
            result.sort(key=lambda x: x.get('name', ''))
            
            logger.info(f"Found {len(result)} available projects")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_available_projects: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_available_projects: {e}")
            raise
    
    async def get_available_trackers(self) -> List[Dict]:
        """Get list of available trackers for filtering"""
        try:
            trackers = self.redmine.tracker.all()
            result = []
            
            for tracker in trackers:
                result.append({
                    'id': getattr(tracker, 'id', ''),
                    'name': getattr(tracker, 'name', '')
                })
            
            # Sort by name
            result.sort(key=lambda x: x.get('name', ''))
            
            logger.info(f"Found {len(result)} available trackers")
            return result
            
        except RedmineError as e:
            logger.error(f"Redmine API error in get_available_trackers: {e}")
            raise  
        except Exception as e:
            logger.error(f"Error in get_available_trackers: {e}")
            raise
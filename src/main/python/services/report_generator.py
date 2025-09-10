#!/usr/bin/env python3
"""
Report Generator Service

Service for generating Redmine reports.
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Optional
from .email_service import EmailService
from .redmine_service import RedmineService

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Service for report generation"""
    
    def __init__(self, settings, redmine_service: RedmineService = None, email_service: EmailService = None):
        self.settings = settings
        self.redmine_service = redmine_service or RedmineService(settings)
        self.email_service = email_service or EmailService(settings)
        logger.info("Initialized Report Generator service")
    
    async def generate_and_send_report1(self, recipients: Optional[List[str]] = None) -> dict:
        """Generate and send Report 1 - Progress Statistics"""
        try:
            logger.info("Starting Report 1 generation")
            
            # Get date range (default: last 14 days)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=getattr(self.settings, 'REPORT_DAYS', 14))
            
            # Generate report data
            table1_data = await self.redmine_service.get_issue_statistics(start_date, end_date)
            table2_data = await self.redmine_service.get_issue_list(start_date, end_date)
            
            # Generate HTML report
            html_content = self._generate_report1_html(table1_data, table2_data, start_date, end_date)
            
            # Determine recipients
            if not recipients:
                # Get all Redmine users as default recipients
                recipients = await self._get_default_recipients(table1_data + table2_data)
            
            # Send email
            subject = f"Redmine 進度報表 - {start_date.strftime('%Y/%m/%d')} 至 {end_date.strftime('%Y/%m/%d')}"
            success = await self.email_service.send_report_email(subject, html_content, recipients)
            
            result = {
                "status": "success" if success else "failed",
                "message": f"Report 1 {'sent successfully' if success else 'failed to send'}",
                "recipients": recipients,
                "data_summary": {
                    "assignee_count": len(table1_data),
                    "issue_count": len(table2_data),
                    "date_range": f"{start_date} to {end_date}"
                }
            }
            
            logger.info(f"Report 1 generation completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate Report 1: {e}")
            raise
    
    async def generate_and_send_report2(self, recipients: Optional[List[str]] = None, update_date: Optional[date] = None) -> dict:
        """Generate and send Report 2 - Due Date Changes"""
        try:
            logger.info("Starting Report 2 generation")
            
            # Use provided date or default to today
            if not update_date:
                update_date = datetime.now().date()
            
            # Generate report data
            changes_data = await self.redmine_service.get_due_date_changes("open", update_date)
            
            # Generate HTML report
            html_content = self._generate_report2_html(changes_data, update_date)
            
            # Determine recipients
            if not recipients:
                # Get all Redmine users as default recipients
                recipients = await self._get_default_recipients_report2(changes_data)
            
            # Send email
            subject = f"Redmine 完成日期異動報表 - {update_date.strftime('%Y/%m/%d')}"
            success = await self.email_service.send_report_email(subject, html_content, recipients)
            
            result = {
                "status": "success" if success else "failed",
                "message": f"Report 2 {'sent successfully' if success else 'failed to send'}",
                "recipients": recipients,
                "data_summary": {
                    "changes_count": len(changes_data),
                    "update_date": str(update_date)
                }
            }
            
            logger.info(f"Report 2 generation completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate Report 2: {e}")
            raise
    
    async def generate_and_send_report3(self, recipients: Optional[List[str]] = None) -> dict:
        """Generate and send Report 3 - Special Projects (專項用)"""
        try:
            logger.info("Starting Report 3 generation")
            
            # Get date range (default: last 14 days)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=getattr(self.settings, 'REPORT_DAYS', 14))
            
            # Generate report data for special projects
            table1_data = await self.redmine_service.get_special_project_statistics(start_date, end_date)
            table2_data = await self.redmine_service.get_special_project_issue_list(start_date, end_date)
            
            # Generate HTML report
            html_content = self._generate_report3_html(table1_data, table2_data, start_date, end_date)
            
            # Determine recipients
            if not recipients:
                # Get all Redmine users as default recipients
                recipients = await self._get_default_recipients(table1_data + table2_data)
            
            # Send email
            subject = f"專項用專案報表 - {start_date.strftime('%Y/%m/%d')} 至 {end_date.strftime('%Y/%m/%d')}"
            success = await self.email_service.send_report_email(subject, html_content, recipients)
            
            result = {
                "status": "success" if success else "failed",
                "message": f"Report 3 {'sent successfully' if success else 'failed to send'}",
                "recipients": recipients,
                "data_summary": {
                    "assignee_count": len(table1_data),
                    "issue_count": len(table2_data),
                    "date_range": f"{start_date} to {end_date}",
                    "project_type": "專項用專案"
                }
            }
            
            logger.info(f"Report 3 generation completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate Report 3: {e}")
            raise
    
    async def _get_default_recipients(self, data: List) -> List[str]:
        """Get all Redmine users as default recipients"""
        try:
            # Get all Redmine users
            users = await self.redmine_service.get_users()
            emails = [user['email'] for user in users if user.get('email')]
            
            logger.info(f"Found {len(emails)} Redmine user emails for recipients")
            return emails or [self.settings.EMAIL_FROM]
            
        except Exception as e:
            logger.error(f"Error getting default recipients: {e}")
            return [self.settings.EMAIL_FROM]
    
    async def _get_default_recipients_report2(self, data: List) -> List[str]:
        """Get all Redmine users as default recipients for report 2"""
        return await self._get_default_recipients(data)
    
    def _generate_report1_html(self, table1_data: List, table2_data: List, start_date: date, end_date: date) -> str:
        """Generate HTML content for Report 1"""
        # Build statistics table
        table1_html = self._build_statistics_table(table1_data)
        
        # Build issues list table
        table2_html = self._build_issues_table(table2_data)
        
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .date-range {{ color: #666; margin-bottom: 20px; }}
                .status-note {{ color: #666; font-size: 0.9em; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>Redmine 任務總欄</h1>
            <p class="date-range">報表期間: {start_date.strftime('%Y/%m/%d')} 至 {end_date.strftime('%Y/%m/%d')}</p>
            
            <h2>1. 議題統計 (依角色與被分派者)</h2>
            {table1_html}
            
            <h2>2. 詳細議題清單</h2>
            {table2_html}
            
            <p><small>此報表由 Redmine 自動報表系統生成於 {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}</small></p>
        </body>
        </html>
        """
    
    def _generate_report2_html(self, changes_data: List, update_date: date) -> str:
        """Generate HTML content for Report 2"""
        # Build changes table
        changes_html = self._build_changes_table(changes_data)
        
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .date-range {{ color: #666; margin-bottom: 20px; }}
                .adjustment-positive {{ color: #d9534f; }}
                .adjustment-negative {{ color: #5cb85c; }}
                .priority-high {{ background-color: #fff3cd; color: #856404; }}
                .priority-urgent {{ background-color: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <h1>任務進度變更進度表</h1>
            <p class="date-range">異動日期: {update_date.strftime('%Y/%m/%d')}</p>
            
            <h2>完成日期異動清單</h2>
            {changes_html}
            
            <p><small>此報表由 Redmine 自動報表系統生成於 {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}</small></p>
        </body>
        </html>
        """
    
    def _generate_report3_html(self, table1_data: List, table2_data: List, start_date: date, end_date: date) -> str:
        """Generate HTML content for Report 3 - Special Projects"""
        # Build statistics table
        table1_html = self._build_statistics_table(table1_data)
        
        # Build issues list table
        table2_html = self._build_issues_table(table2_data)
        
        return f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .date-range {{ color: #666; margin-bottom: 20px; }}
                .status-note {{ color: #666; font-size: 0.9em; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>專項用專案報表</h1>
            <p class="date-range">報表期間: {start_date.strftime('%Y/%m/%d')} 至 {end_date.strftime('%Y/%m/%d')}</p>
            
            <h2>1. 專項用專案議題統計 (依角色與被分派者)</h2>
            {table1_html}
            
            <h2>2. 專項用專案詳細議題清單</h2>
            {table2_html}
            
            <p><small>此報表由 Redmine 自動報表系統生成於 {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}</small></p>
        </body>
        </html>
        """
    
    def _build_statistics_table(self, data: List) -> str:
        """Build HTML table for statistics data with ordered statuses"""
        if not data:
            return "<p>無統計資料</p>"
        
        # Use predefined status order from RedmineService
        status_order = self.redmine_service.get_status_order()
        status_note = self.redmine_service.get_status_aggregation_note()
        
        html = "<table><thead><tr><th>角色</th><th>被分派者</th>"
        for status in status_order:
            html += f"<th>{status}</th>"
        html += "</tr></thead><tbody>"
        
        for row in data:
            html += f"<tr><td>{row.get('role', '')}</td><td>{row.get('assignee', '')}</td>"
            for status in status_order:
                html += f"<td>{row.get(status, 0)}</td>"
            html += "</tr>"
        
        html += "</tbody></table>"
        html += f"<p class='status-note'><em>{status_note}</em></p>"
        return html
    
    def _build_issues_table(self, data: List) -> str:
        """Build HTML table for issues data"""
        if not data:
            return "<p>無議題資料</p>"
        
        html = """
        <table>
        <thead>
            <tr>
                <th>專案</th><th>優先權</th><th>追蹤標籤</th><th>被分派者</th><th>狀態</th>
                <th>主旨</th><th>完工日期</th><th>開始日期</th><th>更新時間</th>
            </tr>
        </thead>
        <tbody>
        """
        
        current_project = ''
        project_index = 0
        
        for row in data:
            # Check if project changed
            project_name = row.get('project', '')
            if current_project != project_name:
                current_project = project_name
                project_index += 1
            
            # Alternate background color based on project
            bg_color = '#f8f9fa' if project_index % 2 == 0 else '#ffffff'
            
            html += f"""
            <tr style="background-color: {bg_color};">
                <td>{project_name}</td>
                <td>{row.get('priority', '')}</td>
                <td>{row.get('tracker', '')}</td>
                <td>{row.get('assigned_to', '')}</td>
                <td>{row.get('status', '')}</td>
                <td>{row.get('subject', '')}</td>
                <td>{row.get('due_date', '')}</td>
                <td>{row.get('start_date', '')}</td>
                <td>{row.get('updated_on', '')}</td>
            </tr>
            """
        
        html += "</tbody></table>"
        return html
    
    def _build_changes_table(self, data: List) -> str:
        """Build HTML table for due date changes"""
        if not data:
            return "<p>本日無完成日期異動</p>"
        
        html = """
        <table>
        <thead>
            <tr>
                <th>專案</th><th>優先權</th><th>主旨</th><th>異動者</th><th>被分派者</th>
                <th>新完成日期</th><th>原完成日期</th><th>調整天數</th><th>異動時間</th>
            </tr>
        </thead>
        <tbody>
        """
        
        for row in data:
            adjustment_class = ""
            adjustment = row.get('days_adjustment', '')
            if adjustment.startswith('+'):
                adjustment_class = "adjustment-positive"
            elif adjustment.startswith('-'):
                adjustment_class = "adjustment-negative"
            
            # Priority color coding
            priority = row.get('priority', '')
            priority_class = ""
            if priority == '高':
                priority_class = "priority-high"
            elif priority == '急':
                priority_class = "priority-urgent"
            
            html += f"""
            <tr>
                <td>{row.get('project', '')}</td>
                <td class="{priority_class}">{priority}</td>
                <td>{row.get('subject', '')}</td>
                <td>{row.get('modifier', '')}</td>
                <td>{row.get('assigned_to', '')}</td>
                <td>{row.get('new_due_date', '')}</td>
                <td>{row.get('old_due_date', '')}</td>
                <td class="{adjustment_class}">{adjustment}</td>
                <td>{row.get('change_date', '')}</td>
            </tr>
            """
        
        html += "</tbody></table>"
        return html
    
    async def generate_and_send_report5(self, recipients: Optional[List[str]] = None, days: int = 14, 
                                       project_filter: str = None) -> dict:
        """Generate and send Report 5 - Construction Photos"""
        try:
            logger.info("Starting Report 5 generation")
            
            # Get construction photos data
            from .photo_service import PhotoService
            photo_service = PhotoService(self.settings)
            
            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            photos_data = await photo_service.get_construction_photos(
                start_date=start_date, 
                end_date=end_date, 
                project_filter=project_filter
            )
            
            # Generate HTML report
            html_content = self._generate_report5_html(photos_data, start_date, end_date, project_filter)
            
            # Determine recipients
            if not recipients:
                # Get all Redmine users as default recipients
                recipients = await self._get_default_recipients(photos_data)
            
            # Send email
            filter_text = f" (專案: {project_filter})" if project_filter else ""
            subject = f"近期施工照片報表{filter_text} - {start_date.strftime('%Y/%m/%d')} 至 {end_date.strftime('%Y/%m/%d')}"
            success = await self.email_service.send_report_email(subject, html_content, recipients)
            
            result = {
                "status": "success" if success else "failed",
                "message": f"Report 5 {'sent successfully' if success else 'failed to send'}",
                "recipients": recipients,
                "data_summary": {
                    "projects_count": len(set([item['project_name'] for item in photos_data])),
                    "photos_count": sum([item['photo_count'] for item in photos_data]),
                    "date_range": f"{start_date} to {end_date}",
                    "project_filter": project_filter or "所有專案"
                }
            }
            
            logger.info(f"Report 5 generation completed: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate Report 5: {e}")
            raise
    
    def _generate_report5_html(self, photos_data: List, start_date: date, end_date: date, 
                              project_filter: str = None) -> str:
        """Generate HTML content for Report 5 (Construction Photos)"""
        
        # Basic template
        filter_text = f" (專案過濾: {project_filter})" if project_filter else ""
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>近期施工照片報表</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; text-align: center; }}
                h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .photos {{ display: flex; gap: 10px; flex-wrap: wrap; }}
                .photo {{ max-width: 100px; max-height: 75px; border-radius: 4px; }}
                .date-info {{ font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <h1>近期施工照片報表{filter_text}</h1>
            <p class="date-info">報表期間: {start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')}</p>
            
            <h2>施工照片記錄</h2>
        """
        
        if not photos_data:
            html += "<p>查詢期間內無施工照片記錄</p>"
        else:
            html += """
            <table>
                <thead>
                    <tr>
                        <th>專案名稱</th>
                        <th>施工日期</th>
                        <th>施工內容</th>
                        <th>照片數量</th>
                        <th>施工照片</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for item in photos_data:
                # Generate photo thumbnails
                photo_html = ""
                for photo in item['photos'][:3]:  # Show max 3 photos
                    if photo.get('thumbnail_base64'):
                        photo_html += f'<img src="{photo["thumbnail_base64"]}" class="photo" alt="{photo["filename"]}" title="{photo["filename"]}">'
                
                if not photo_html:
                    photo_html = "無照片"
                
                html += f"""
                <tr>
                    <td>{item['project_name']}</td>
                    <td>{item['construction_date']}</td>
                    <td>{item['construction_description']}</td>
                    <td>{item['photo_count']}</td>
                    <td><div class="photos">{photo_html}</div></td>
                </tr>
                """
            
            html += "</tbody></table>"
        
        html += """
            <br>
            <p><small>本報表由Redmine報表系統自動產生</small></p>
        </body>
        </html>
        """
        
        return html
    
    async def generate_and_send_report(self, force=False, email_override=None) -> dict:
        """Generate and send default report (Report 1)"""
        recipients = [email_override] if email_override else None
        return await self.generate_and_send_report1(recipients=recipients)
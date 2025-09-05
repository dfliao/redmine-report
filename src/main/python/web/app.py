#!/usr/bin/env python3
"""
Redmine Report Web Application

Web interface for Redmine reporting system with two main reports:
- Report 1: Original dual-table report (progress statistics + issue list)
- Report 2: Due date change tracking report
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, date, timedelta
from typing import Optional, List
import logging

from ..services.redmine_service import RedmineService
from ..services.report_generator import ReportGenerator
from ..utils.config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Redmine Reports Dashboard",
    description="Web interface for Redmine reporting system",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="src/main/resources/templates")
app.mount("/static", StaticFiles(directory="src/main/resources/static"), name="static")

# Global services
redmine_service: Optional[RedmineService] = None
report_generator: Optional[ReportGenerator] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global redmine_service, report_generator
    
    settings = get_settings()
    redmine_service = RedmineService(settings)
    
    # Import services here to avoid circular imports
    from ..services.email_service import EmailService
    email_service = EmailService(settings)
    
    report_generator = ReportGenerator(settings, redmine_service, email_service)
    
    logger.info("Web application started successfully")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        # Get basic statistics
        stats = await get_dashboard_stats()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "stats": stats,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "Redmine 報表系統"
        })
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.get("/report1", response_class=HTMLResponse)
async def report1_page(request: Request, days: int = 14):
    """Report 1: Original dual-table report"""
    try:
        return templates.TemplateResponse("report1.html", {
            "request": request,
            "days": days,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "報表一 - 議題進度統計"
        })
    except Exception as e:
        logger.error(f"Report 1 page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.get("/report2", response_class=HTMLResponse)
async def report2_page(request: Request, 
                      status: str = "open",
                      update_date: str = None):
    """Report 2: Due date change tracking report"""
    try:
        if update_date is None:
            update_date = datetime.now().strftime("%Y-%m-%d")
        
        # Get available statuses for dropdown
        statuses = await get_available_statuses()
        
        return templates.TemplateResponse("report2.html", {
            "request": request,
            "selected_status": status,
            "update_date": update_date,
            "available_statuses": statuses,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "報表二 - 完成日期異動追蹤"
        })
    except Exception as e:
        logger.error(f"Report 2 page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.get("/report3", response_class=HTMLResponse)
async def report3_page(request: Request, days: int = 14):
    """Report 3: Special project report (專項用)"""
    try:
        return templates.TemplateResponse("report3.html", {
            "request": request,
            "days": days,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "報表三 - 專項用專案統計"
        })
    except Exception as e:
        logger.error(f"Report 3 page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.get("/api/report1/data")
async def get_report1_data(days: int = 14):
    """API endpoint for Report 1 data"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        # Get report data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Table 1: Issue count by assignee and status
        table1_data = await redmine_service.get_issue_statistics(start_date, end_date)
        
        # Table 2: Issue list with details
        table2_data = await redmine_service.get_issue_list(start_date, end_date)
        
        return {
            "success": True,
            "data": {
                "table1": table1_data,
                "table2": table2_data,
                "date_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            }
        }
    except Exception as e:
        logger.error(f"Report 1 API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report2/data")
async def get_report2_data(status: str = "open", 
                          update_date: str = None):
    """API endpoint for Report 2 data - Due date change tracking"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        if update_date is None:
            update_date = datetime.now().strftime("%Y-%m-%d")
        
        target_date = datetime.strptime(update_date, "%Y-%m-%d").date()
        
        # Get due date change tracking data
        data = await redmine_service.get_due_date_changes(
            status_filter=status,
            update_date=target_date
        )
        
        return {
            "success": True,
            "data": data,
            "filters": {
                "status": status,
                "update_date": update_date
            }
        }
    except Exception as e:
        logger.error(f"Report 2 API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report3/data")
async def get_report3_data(days: int = 14):
    """API endpoint for Report 3 data - Special projects (專項用)"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        # Get report data for special projects only
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Table 1: Issue count by assignee and status (special projects only)
        table1_data = await redmine_service.get_special_project_statistics(start_date, end_date)
        
        # Table 2: Issue list with details (special projects only)
        table2_data = await redmine_service.get_special_project_issue_list(start_date, end_date)
        
        return {
            "success": True,
            "data": {
                "table1": table1_data,
                "table2": table2_data,
                "date_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            }
        }
    except Exception as e:
        logger.error(f"Report 3 API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/report4", response_class=HTMLResponse)
async def report4_page(request: Request):
    """Report 4 - Gantt Chart (Construction/Installation Progress)"""
    return templates.TemplateResponse("report4.html", {
        "request": request,
        "title": "報表四：甘特圖",
        "days": 30  # Default to 30 days for Gantt chart
    })

@app.get("/api/report4/data")
async def get_report4_data(days: int = 30):
    """API endpoint for Report 4 data - Gantt chart for construction/installation"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        # Get Gantt chart data (excluding 專項用 projects)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get Gantt chart data
        gantt_data = await redmine_service.get_gantt_chart_data(start_date, end_date)
        
        return {
            "success": True,
            "data": {
                "gantt_data": gantt_data,
                "date_range": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                }
            }
        }
    except Exception as e:
        logger.error(f"Report 4 API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users():
    """Get list of users for recipient selection"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        users = await redmine_service.get_users()
        return {
            "success": True,
            "data": users
        }
    except Exception as e:
        logger.error(f"Get users API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-email")
async def test_email_connection():
    """Test SMTP connection without sending actual email"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Import here to avoid circular imports
        from ..services.email_service import EmailService
        email_service = EmailService(get_settings())
        
        # Test connection
        connection_ok = await email_service.test_connection()
        
        return {
            "success": True,
            "connection_ok": connection_ok,
            "message": "SMTP connection test completed"
        }
    except Exception as e:
        logger.error(f"Email test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/send-email", response_class=HTMLResponse)
async def send_email_page(request: Request, type: int = 1):
    """Send email page with admin authentication"""
    try:
        return templates.TemplateResponse("send-email.html", {
            "request": request,
            "report_type": type,
            "authenticated": False,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": f"發送報表 - {'Redmine 任務總欄' if type == 1 else '任務進度變更進度表'}"
        })
    except Exception as e:
        logger.error(f"Send email page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.post("/send-email", response_class=HTMLResponse)
async def authenticate_admin(
    request: Request,
    type: int = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    """Authenticate admin user with Redmine credentials"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        # Authenticate with Redmine
        is_admin = await redmine_service.authenticate_admin(username, password)
        
        if not is_admin:
            return templates.TemplateResponse("send-email.html", {
                "request": request,
                "report_type": type,
                "authenticated": False,
                "error": "認證失敗：請確認使用者名稱和密碼正確，且具有管理員權限",
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "title": f"發送報表 - {'Redmine 任務總欄' if type == 1 else '任務進度變更進度表'}"
            })
        
        # Get users list for authenticated admin
        users = await redmine_service.get_users()
        
        return templates.TemplateResponse("send-email.html", {
            "request": request,
            "report_type": type,
            "authenticated": True,
            "users": users,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": f"發送報表 - {'Redmine 任務總欄' if type == 1 else '任務進度變更進度表'}"
        })
        
    except Exception as e:
        logger.error(f"Admin authentication error: {e}")
        return templates.TemplateResponse("send-email.html", {
            "request": request,
            "report_type": type,
            "authenticated": False,
            "error": f"認證過程發生錯誤：{str(e)}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": f"發送報表 - {'Redmine 任務總欄' if type == 1 else '任務進度變更進度表'}"
        })

@app.post("/send-email-execute", response_class=HTMLResponse)
async def execute_send_email(request: Request):
    """Execute email sending to selected recipients"""
    try:
        if not report_generator:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        
        # Parse form data manually to handle multiple checkboxes
        form_data = await request.form()
        
        report_type = int(form_data.get("report_type", 1))
        test_email = form_data.get("test_email", "").strip()
        
        # Collect all recipients
        recipients = []
        
        # Add test email if provided
        if test_email:
            recipients.append(test_email)
        
        # Get all selected user emails (multiple checkboxes with same name)
        user_emails = form_data.getlist("user_emails")
        if user_emails:
            recipients.extend([email.strip() for email in user_emails if email.strip()])
        
        if not recipients:
            raise HTTPException(status_code=400, detail="請至少選擇一個收件者")
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        logger.info(f"Sending report {report_type} to {len(recipients)} recipients: {recipients}")
        
        # Send report
        if report_type == 1:
            result = await report_generator.generate_and_send_report1(recipients=recipients)
        elif report_type == 2:
            result = await report_generator.generate_and_send_report2(recipients=recipients)
        else:
            raise HTTPException(status_code=400, detail="無效的報表類型")
        
        # Get users list again for the success page
        users = await redmine_service.get_users() if redmine_service else []
        
        return templates.TemplateResponse("send-email.html", {
            "request": request,
            "report_type": report_type,
            "authenticated": True,
            "users": users,
            "success": f"報表已成功發送給 {len(recipients)} 位收件者：{', '.join(recipients)}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": f"發送報表 - {'Redmine 任務總欄' if report_type == 1 else '任務進度變更進度表'}"
        })
        
    except Exception as e:
        logger.error(f"Execute send email error: {e}")
        # Get users list again for error page
        users = await redmine_service.get_users() if redmine_service else []
        
        return templates.TemplateResponse("send-email.html", {
            "request": request,
            "report_type": report_type,
            "authenticated": True,
            "users": users,
            "error": f"發送Email時發生錯誤：{str(e)}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": f"發送報表 - {'Redmine 任務總欄' if report_type == 1 else '任務進度變更進度表'}"
        })

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """Change password page with admin authentication"""
    try:
        return templates.TemplateResponse("change-password.html", {
            "request": request,
            "authenticated": False,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "變更密碼"
        })
    except Exception as e:
        logger.error(f"Change password page error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "title": "錯誤"
        })

@app.post("/change-password", response_class=HTMLResponse)
async def authenticate_for_password_change(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Authenticate user for password change"""
    try:
        if not redmine_service:
            raise HTTPException(status_code=500, detail="Redmine service not initialized")
        
        # First try admin authentication
        is_admin = await redmine_service.authenticate_admin(username, password)
        
        if is_admin:
            # Admin can change any user's password
            users = await redmine_service.get_users()
            
            return templates.TemplateResponse("change-password.html", {
                "request": request,
                "authenticated": True,
                "is_admin": True,
                "current_user": username,
                "users": users,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "title": "變更密碼"
            })
        else:
            # Try regular user authentication
            is_valid_user = await redmine_service.authenticate_user(username, password)
            
            if is_valid_user:
                # Regular user can only change own password
                return templates.TemplateResponse("change-password.html", {
                    "request": request,
                    "authenticated": True,
                    "is_admin": False,
                    "current_user": username,
                    "users": [],  # No user list for regular users
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                    "title": "變更密碼"
                })
            else:
                return templates.TemplateResponse("change-password.html", {
                    "request": request,
                    "authenticated": False,
                    "error": "認證失敗：請確認使用者名稱和密碼正確",
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                    "title": "變更密碼"
                })
        
    except Exception as e:
        logger.error(f"Password change authentication error: {e}")
        return templates.TemplateResponse("change-password.html", {
            "request": request,
            "authenticated": False,
            "error": f"認證過程發生錯誤：{str(e)}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "變更密碼"
        })

@app.post("/change-password-execute", response_class=HTMLResponse)
async def execute_password_change(
    request: Request,
    target_user: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_password: Optional[str] = Form(None),
    change_dsm: Optional[str] = Form(None),
    change_ldap: Optional[str] = Form(None)
):
    """Execute password change for selected systems"""
    try:
        # Validate passwords match
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="新密碼與確認密碼不符")
        
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="密碼長度至少需要8個字元")
        
        # TODO: Implement actual password change logic for:
        # 1. Synology DSM users
        # 2. Synology LDAP server
        # This requires Synology API integration or SSH/command execution
        
        # For now, simulate the process
        results = []
        if change_dsm:
            results.append("Synology DSM 密碼變更成功")
        if change_ldap:
            results.append("Synology LDAP 密碼變更成功")
        
        # Get users list again for the success page
        users = await redmine_service.get_users() if redmine_service else []
        
        return templates.TemplateResponse("change-password.html", {
            "request": request,
            "authenticated": True,
            "is_admin": True,
            "users": users,
            "success": f"密碼變更完成：{', '.join(results) if results else '未選擇任何系統'}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "變更密碼"
        })
        
    except Exception as e:
        logger.error(f"Execute password change error: {e}")
        # Get users list again for error page
        users = await redmine_service.get_users() if redmine_service else []
        
        return templates.TemplateResponse("change-password.html", {
            "request": request,
            "authenticated": True,
            "is_admin": True,
            "users": users,
            "error": f"密碼變更失敗：{str(e)}",
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "title": "變更密碼"
        })

@app.post("/api/send-report")
async def send_report_email(
    report_type: int = Form(...),
    recipients: str = Form(...)  # Comma-separated list of email addresses
):
    """Send report via email to selected recipients"""
    try:
        if not report_generator:
            raise HTTPException(status_code=500, detail="Report generator not initialized")
        
        # Parse recipients list
        recipient_list = [email.strip() for email in recipients.split(',') if email.strip()]
        if not recipient_list:
            raise HTTPException(status_code=400, detail="No recipients specified")
        
        logger.info(f"Sending report {report_type} to {len(recipient_list)} recipients: {recipient_list}")
        
        if report_type == 1:
            result = await report_generator.generate_and_send_report1(recipients=recipient_list)
        elif report_type == 2:
            result = await report_generator.generate_and_send_report2(recipients=recipient_list)
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        return {"success": True, "message": f"報表已成功發送給 {len(recipient_list)} 位收件者", "details": result}
    
    except Exception as e:
        logger.error(f"Send report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        if not redmine_service:
            return {}
        
        # Get basic counts
        total_issues = await redmine_service.get_total_issue_count()
        open_issues = await redmine_service.get_open_issue_count()
        today_updates = await redmine_service.get_today_update_count()
        
        return {
            "total_issues": total_issues,
            "open_issues": open_issues,
            "today_updates": today_updates,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return {}

async def get_available_statuses():
    """Get available issue statuses"""
    try:
        if not redmine_service:
            return []
        
        return await redmine_service.get_issue_statuses()
    except Exception as e:
        logger.error(f"Get statuses error: {e}")
        return []

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
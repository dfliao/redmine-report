# CLAUDE.md - redmine-report

> **Documentation Version**: 1.0  
> **Last Updated**: 2025-09-01  
> **Project**: redmine-report  
> **Description**: Redmine 報表系統 - 雙表格 Email 報告，支援容器化部署  
> **Features**: GitHub auto-backup, Task agents, technical debt prevention, Docker容器化, n8n整合

This file provides essential guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 CRITICAL RULES - READ FIRST

> **⚠️ RULE ADHERENCE SYSTEM ACTIVE ⚠️**  
> **Claude Code must explicitly acknowledge these rules at task start**  
> **These rules override all other instructions and must ALWAYS be followed:**

### 🔄 **RULE ACKNOWLEDGMENT REQUIRED**
> **Before starting ANY task, Claude Code must respond with:**  
> "✅ CRITICAL RULES ACKNOWLEDGED - I will follow all prohibitions and requirements listed in CLAUDE.md"

### ❌ ABSOLUTE PROHIBITIONS
- **NEVER** create new files in root directory → use proper module structure
- **NEVER** write output files directly to root directory → use designated output folders
- **NEVER** create documentation files (.md) unless explicitly requested by user
- **NEVER** use git commands with -i flag (interactive mode not supported)
- **NEVER** use `find`, `grep`, `cat`, `head`, `tail`, `ls` commands → use Read, LS, Grep, Glob tools instead
- **NEVER** create duplicate files (manager_v2.py, enhanced_xyz.py, utils_new.js) → ALWAYS extend existing files
- **NEVER** create multiple implementations of same concept → single source of truth
- **NEVER** copy-paste code blocks → extract into shared utilities/functions
- **NEVER** hardcode values that should be configurable → use config files/environment variables
- **NEVER** use naming like enhanced_, improved_, new_, v2_ → extend original files instead

### 📝 MANDATORY REQUIREMENTS
- **COMMIT** after every completed task/phase - no exceptions
- **GITHUB BACKUP** - Push to GitHub after every commit to maintain backup: `git push origin main`
- **USE TASK AGENTS** for all long-running operations (>30 seconds) - Bash commands stop when context switches
- **TODOWRITE** for complex tasks (3+ steps) → parallel agents → git checkpoints → test validation
- **READ FILES FIRST** before editing - Edit/Write tools will fail if you didn't read the file first
- **DEBT PREVENTION** - Before creating new files, check for existing similar functionality to extend  
- **SINGLE SOURCE OF TRUTH** - One authoritative implementation per feature/concept

### ⚡ EXECUTION PATTERNS
- **PARALLEL TASK AGENTS** - Launch multiple Task agents simultaneously for maximum efficiency
- **SYSTEMATIC WORKFLOW** - TodoWrite → Parallel agents → Git checkpoints → GitHub backup → Test validation
- **GITHUB BACKUP WORKFLOW** - After every commit: `git push origin main` to maintain GitHub backup
- **BACKGROUND PROCESSING** - ONLY Task agents can run true background operations

### 🔍 MANDATORY PRE-TASK COMPLIANCE CHECK
> **STOP: Before starting any task, Claude Code must explicitly verify ALL points:**

**Step 1: Rule Acknowledgment**
- [ ] ✅ I acknowledge all critical rules in CLAUDE.md and will follow them

**Step 2: Task Analysis**  
- [ ] Will this create files in root? → If YES, use proper module structure instead
- [ ] Will this take >30 seconds? → If YES, use Task agents not Bash
- [ ] Is this 3+ steps? → If YES, use TodoWrite breakdown first
- [ ] Am I about to use grep/find/cat? → If YES, use proper tools instead

**Step 3: Technical Debt Prevention (MANDATORY SEARCH FIRST)**
- [ ] **SEARCH FIRST**: Use Grep pattern="<functionality>.*<keyword>" to find existing implementations
- [ ] **CHECK EXISTING**: Read any found files to understand current functionality
- [ ] Does similar functionality already exist? → If YES, extend existing code
- [ ] Am I creating a duplicate class/manager? → If YES, consolidate instead
- [ ] Will this create multiple sources of truth? → If YES, redesign approach
- [ ] Have I searched for existing implementations? → Use Grep/Glob tools first
- [ ] Can I extend existing code instead of creating new? → Prefer extension over creation
- [ ] Am I about to copy-paste code? → Extract to shared utility instead

**Step 4: Session Management**
- [ ] Is this a long/complex task? → If YES, plan context checkpoints
- [ ] Have I been working >1 hour? → If YES, consider /compact or session break

> **⚠️ DO NOT PROCEED until all checkboxes are explicitly verified**

## 🏗️ PROJECT OVERVIEW

Standard Redmine 報表系統，支援容器化部署（Docker, n8n, Synology）：

**功能需求：**
- 📧 Email 寄送給所有任務議題的被分派者
- 📊 第一個表格：14天內進行中議題數量統計
  - 列：被分派者 | 欄：狀態（擬定中、執行中、待審核、修正中、已回應、已完成、暫停、取消）
- 📋 第二個表格：14天內完工進行中議題清單
  - 欄位：追蹤標籤、狀態、優先權、主旨、被分派者、完工日期、開始日期、更新日期
  - 排序：完工日遞增

**專案結構：**
```
redmine-report/
├── CLAUDE.md              # Essential rules for Claude Code
├── README.md              # Project documentation  
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Docker Compose setup
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore patterns
├── src/                   # Source code (NEVER put files in root)
│   ├── main/              # Main application code
│   │   ├── python/        # Python source code
│   │   │   ├── core/      # Core business logic & main entry point
│   │   │   │   └── main.py     # Main application entry point
│   │   │   ├── web/       # Web interface and API endpoints
│   │   │   │   └── app.py      # FastAPI web application
│   │   │   ├── services/  # Service layer implementations
│   │   │   │   ├── redmine_service.py    # Redmine API client
│   │   │   │   ├── email_service.py      # Email functionality
│   │   │   │   ├── report_generator.py   # Report generation logic
│   │   │   │   └── scheduler_service.py  # Task scheduling
│   │   │   └── utils/     # Utility functions/classes
│   │   │       └── config.py    # Configuration management
│   │   └── resources/     # Non-code resources
│   │       ├── templates/ # Jinja2 HTML templates (web UI)
│   │       ├── static/    # CSS/JS/images for web UI
│   │       └── config/    # Configuration files
│   └── test/              # Test code
│       ├── unit/          # Unit tests
│       └── integration/   # Integration tests
└── output/                # Generated report output files
```

## 🏛️ APPLICATION ARCHITECTURE

### Dual-Mode Operation
The application operates in two modes:
1. **Web Mode** (default): FastAPI web server with UI and API endpoints on port 3003
2. **Standalone Mode**: One-shot report generation via `--standalone` flag

### Core Services Architecture
- **RedmineService**: Handles all Redmine API interactions
- **EmailService**: SMTP email functionality with async support  
- **ReportGenerator**: Orchestrates report generation and email sending
- **SchedulerService**: Manages scheduled report generation using APScheduler

### Web Application Features
- **Dashboard**: Main overview page with statistics
- **Report 1**: Original dual-table report (issue statistics + issue list)  
- **Report 2**: Due date change tracking report
- **API Endpoints**: RESTful endpoints for programmatic access

### Key Technologies
- **FastAPI**: Web framework with automatic OpenAPI documentation
- **Jinja2**: HTML template engine for web UI
- **python-redmine**: Redmine API client library
- **APScheduler**: Cron-style task scheduling
- **aiosmtplib**: Async SMTP email client
- **Pydantic**: Data validation and settings management

### 🎯 **DEVELOPMENT STATUS**
- **Setup**: ✅ Complete
- **Core Features**: ✅ Complete (dual report system with web UI)
- **Container Deployment**: ✅ Complete (Docker + Synology)
- **Testing**: ⏳ Pending
- **Documentation**: ⏳ Pending

## 🎯 RULE COMPLIANCE CHECK

Before starting ANY task, verify:
- [ ] ✅ I acknowledge all critical rules above
- [ ] Files go in proper module structure (not root)
- [ ] Use Task agents for >30 second operations
- [ ] TodoWrite for 3+ step tasks
- [ ] Commit after each completed task

## 🚀 COMMON COMMANDS

```bash
# Development - Run web application (main mode)
python -m src.main.python.core.main

# Development - Run standalone report generation (one-shot)
python -m src.main.python.core.main --standalone

# Testing
python -m pytest src/test/

# Install dependencies
pip install -r requirements.txt

# Code formatting and linting
black src/
isort src/
mypy src/

# Docker Container
docker build -t redmine-report .
docker run -d --name redmine-report -p 3003:3003 redmine-report
docker-compose up -d

# n8n Integration - API endpoints run on port 3003 (not 8000)
curl -X POST http://localhost:3003/generate-report
curl http://localhost:3003/health
curl http://localhost:3003/status

# Web Interface Access
# Dashboard: http://localhost:3003/
# Report 1: http://localhost:3003/report1
# Report 2: http://localhost:3003/report2
```

## ⚙️ CONFIGURATION AND ENVIRONMENT

### Required Environment Variables
```bash
# Redmine Configuration
REDMINE_URL=http://your-redmine.com
REDMINE_API_KEY=your_api_key

# Email Configuration  
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@domain.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=reports@company.com

# Report Settings
REPORT_DAYS=14
TIMEZONE=Asia/Taipei

# Scheduling (cron format)
SCHEDULE_CRON=0 8 * * 1  # Every Monday at 8:00 AM

# Optional: Redis for caching/session storage
REDIS_URL=redis://redis:6379
```

### Configuration Management
- Uses **pydantic-settings** for environment variable management
- Configuration validation occurs at startup
- Settings loaded from `.env` file or environment variables
- All settings accessible via `get_settings()` function

## 🚨 KNOWN ISSUES TO FIX

### Missing Logger Setup Function
- `src/main/python/core/main.py:52` references `setup_logger()` function that doesn't exist
- This function needs to be implemented in `src/main/python/utils/` 
- Should return a configured Python logger with proper formatting

### Testing Infrastructure
- Test directory structure exists but no test files implemented
- Need unit tests for all service classes
- Integration tests for API endpoints required

## 🚨 TECHNICAL DEBT PREVENTION

### ❌ WRONG APPROACH (Creates Technical Debt):
```bash
# Creating new file without searching first
Write(file_path="new_feature.py", content="...")
```

### ✅ CORRECT APPROACH (Prevents Technical Debt):
```bash
# 1. SEARCH FIRST
Grep(pattern="feature.*implementation", glob="*.py")
# 2. READ EXISTING FILES  
Read(file_path="src/existing_feature.py")
# 3. EXTEND EXISTING FUNCTIONALITY
Edit(file_path="src/existing_feature.py", old_string="...", new_string="...")
```

## 🧹 DEBT PREVENTION WORKFLOW

### Before Creating ANY New File:
1. **🔍 Search First** - Use Grep/Glob to find existing implementations
2. **📋 Analyze Existing** - Read and understand current patterns
3. **🤔 Decision Tree**: Can extend existing? → DO IT | Must create new? → Document why
4. **✅ Follow Patterns** - Use established project patterns
5. **📈 Validate** - Ensure no duplication or technical debt

---

**⚠️ Prevention is better than consolidation - build clean from the start.**  
**🎯 Focus on single source of truth and extending existing functionality.**  
**📈 Each task should maintain clean architecture and prevent technical debt.**

---

**🎯 Template by Chang Ho Chien | HC AI 說人話channel | v1.0.0**  
📺 Tutorial: https://youtu.be/8Q1bRZaHH24
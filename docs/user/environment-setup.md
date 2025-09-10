# 環境配置指南

本文件說明 Redmine Report Generator 在你的特定環境中的配置方式。

## 🖥️ 環境規格

- **Synology NAS**: Container Manager
- **n8n**: 版本 1.107.4
- **Redmine**: 版本 6.0.6
- **Email Server**: Synology MailPlus Server
- **寄送者**: GOPEAK@mail.gogopeaks.com

## ⚙️ 環境變數配置

### 完整的 .env 配置範例

```env
# ================================
# Redmine 6.0.6 Configuration
# ================================
REDMINE_URL=http://your-redmine-server:3000
REDMINE_API_KEY=your_redmine_6_0_6_api_key

# Redmine 6.0.6 特定設定
REDMINE_VERSION=6.0.6
REDMINE_TIMEOUT=30
REDMINE_VERIFY_SSL=true

# ================================
# Synology MailPlus Server
# ================================
SMTP_HOST=your-synology-nas.local
SMTP_PORT=587
SMTP_USERNAME=GOPEAK@mail.gogopeaks.com
SMTP_PASSWORD=your_mailplus_password
EMAIL_FROM=GOPEAK@mail.gogopeaks.com
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false

# MailPlus 特定設定
EMAIL_TIMEOUT=60
EMAIL_RETRY_ATTEMPTS=3
EMAIL_RETRY_DELAY=5

# ================================
# Report Configuration
# ================================
REPORT_DAYS=14
TIMEZONE=Asia/Taipei

# 報表主旨格式
EMAIL_SUBJECT_TEMPLATE=【Redmine報表】{date} - 議題進度統計
EMAIL_CHARSET=utf-8

# ================================
# n8n 1.107.4 Integration
# ================================
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# n8n webhook 配置
N8N_WEBHOOK_URL=http://n8n:5678/webhook/redmine-report
N8N_VERSION=1.107.4

# ================================
# Synology Container Manager
# ================================
# 排程設定 (cron format)
SCHEDULE_CRON=0 8 * * 1  # 每週一早上8點

# 容器最佳化
MAX_WORKERS=2
WORKER_TIMEOUT=300
LOG_LEVEL=INFO

# 資源限制
MEMORY_LIMIT=256M
CPU_LIMIT=0.8

# ================================
# Synology LDAP Configuration
# ================================
LDAP_HOST=192.168.0.222
LDAP_PORT=389
LDAP_ADMIN_DN=uid=df.liao,cn=users,dc=nas,dc=gogopeaks,dc=com
LDAP_ADMIN_PASS=your_ldap_admin_password_here
LDAP_BASE_DN=dc=nas,dc=gogopeaks,dc=com
LDAP_LOGIN_ATTR=uid

# LDAP 連線設定
LDAP_TIMEOUT=30
LDAP_USE_TLS=false

# ================================
# Synology DSM API Configuration  
# ================================
SYNOLOGY_DSM_HOST=192.168.0.222
SYNOLOGY_DSM_PORT=5001
SYNOLOGY_DSM_ADMIN_USER=admin
SYNOLOGY_DSM_ADMIN_PASS=your_synology_admin_password_here

# DSM API 設定
DSM_VERIFY_SSL=false
DSM_TIMEOUT=30

# ================================
# Photo Service Configuration
# ================================
PHOTO_BASE_PATH=/volume4/photo/@@案場施工照片

# 照片服務設定
PHOTO_THUMBNAIL_SIZE=200x150
PHOTO_MAX_COUNT=3
PHOTO_SUPPORTED_FORMATS=jpg,jpeg,png,heic,heif,tiff,bmp

# ================================
# Security & Performance
# ================================
DEBUG=false
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:5678,http://n8n:5678

# 快取設定 (如果使用 Redis)
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# ================================
# Logging Configuration
# ================================
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/app/logs/app.log
LOG_ROTATION=daily
LOG_RETENTION_DAYS=30
```

## 🔧 n8n 1.107.4 工作流程設定

### 1. HTTP Request 節點配置

適用於 n8n 1.107.4 的節點設定：

```json
{
  "name": "Generate Redmine Report",
  "type": "n8n-nodes-base.httpRequest",
  "parameters": {
    "method": "POST",
    "url": "http://redmine-report:8000/generate-report",
    "authentication": "none",
    "requestFormat": "json",
    "bodyParameters": {
      "parameters": [
        {
          "name": "force",
          "value": "true"
        }
      ]
    },
    "options": {
      "timeout": 300000,
      "retry": {
        "enabled": true,
        "maxTries": 3,
        "waitBetweenTries": 5000
      }
    }
  }
}
```

### 2. Cron Trigger 節點

```json
{
  "name": "Weekly Report Trigger",
  "type": "n8n-nodes-base.cron",
  "parameters": {
    "rule": {
      "interval": [
        {
          "field": "cronExpression",
          "expression": "0 8 * * 1"
        }
      ]
    }
  }
}
```

### 3. Email 通知節點 (MailPlus)

```json
{
  "name": "Send Notification",
  "type": "n8n-nodes-base.emailSend",
  "parameters": {
    "fromEmail": "GOPEAK@mail.gogopeaks.com",
    "toEmail": "admin@gogopeaks.com",
    "subject": "Redmine 報表生成完成",
    "emailFormat": "html",
    "message": "<h3>報表生成結果</h3><p>狀態: {{$json.success}}</p><p>詳情: {{$json.message}}</p>",
    "options": {
      "smtpHost": "your-synology-nas.local",
      "smtpPort": 587,
      "smtpUser": "GOPEAK@mail.gogopeaks.com",
      "smtpPassword": "your_mailplus_password",
      "smtpSecure": "starttls"
    }
  }
}
```

## 📊 Redmine 6.0.6 API 配置

### API 金鑰取得

1. 登入 Redmine 6.0.6 管理介面
2. 前往 **我的帳戶** → **API存取金鑰**
3. 點選 **顯示** 並複製 API Key
4. 將金鑰加入 `.env` 檔案的 `REDMINE_API_KEY`

### 必要權限設定

確保 API 用戶具備以下權限：
- ✅ 查看議題
- ✅ 查看專案
- ✅ 查看用戶資訊
- ✅ 查看時間記錄 (如需要)

### API 端點測試

```bash
# 測試 API 連接性
curl -H "X-Redmine-API-Key: YOUR_API_KEY" \
     http://your-redmine-server:3000/issues.json?limit=1

# 測試專案列表
curl -H "X-Redmine-API-Key: YOUR_API_KEY" \
     http://your-redmine-server:3000/projects.json

# 測試用戶列表
curl -H "X-Redmine-API-Key: YOUR_API_KEY" \
     http://your-redmine-server:3000/users.json
```

## 📧 Synology MailPlus 設定

### SMTP 伺服器設定

在 Synology MailPlus Server 中：

1. **SMTP 服務**: 確保已啟用
2. **連接埠**: 587 (STARTTLS) 或 25 (不加密)
3. **驗證**: 啟用 SMTP 驗證
4. **TLS/SSL**: 建議使用 STARTTLS (port 587)

### 郵件帳戶設定

為 `GOPEAK@mail.gogopeaks.com` 帳戶設定：

1. **郵件格式**: HTML + 純文字
2. **附件大小**: 建議至少 10MB (Excel 報表)
3. **發送限制**: 確保沒有每日發送限制
4. **白名單**: 將報表接收者加入白名單

### 防火牆設定

確保 Synology NAS 的防火牆允許：
- **SMTP 出站**: 埠 587 (或 25)
- **Container 通訊**: Docker 內部網路
- **n8n 存取**: 埠 8000 (API)
- **LDAP 存取**: 埠 389 (LDAP)

## 🔐 Synology LDAP 伺服器設定

### LDAP 服務配置

在 Synology DSM 中設定 LDAP 伺服器：

1. **DSM 套件中心**: 安裝 "LDAP Server"
2. **LDAP 伺服器設定**:
   - Base DN: `dc=nas,dc=gogopeaks,dc=com`
   - 管理員帳戶: `uid=df.liao,cn=users,dc=nas,dc=gogopeaks,dc=com`
   - 啟用密碼變更功能

3. **使用者帳戶**: 確保所有 Redmine 使用者在 LDAP 中存在

### LDAP 管理員密碼設定

**重要**: `LDAP_ADMIN_PASS` 必須設定，否則密碼變更功能無法使用

```bash
# 設定 LDAP 管理員密碼 (通常與 DSM 管理員密碼相同)
LDAP_ADMIN_PASS=your_dsm_admin_password
```

### 測試 LDAP 連線

```bash
# 測試 LDAP 連線
ldapsearch -x -h 192.168.0.222 -p 389 \
    -D "uid=df.liao,cn=users,dc=nas,dc=gogopeaks,dc=com" \
    -W -b "dc=nas,dc=gogopeaks,dc=com" \
    "(objectClass=person)"
```

## 🔑 Synology DSM API 設定

### DSM API 啟用

1. **DSM 控制台** → **終端機與 SNMP**
2. 啟用 **SSH 服務** (如需要)
3. **DSM API**: 預設啟用於 5001 埠

### 管理員帳戶設定

確保 DSM 管理員帳戶具備：
- ✅ 系統管理權限
- ✅ LDAP 管理權限
- ✅ 使用者管理權限

## 🚀 部署驗證清單

部署完成後，請依序檢查：

### 1. 容器健康檢查
```bash
curl http://your-nas-ip:8000/health
# 預期回應: {"status":"healthy","version":"1.0.0"}
```

### 2. Redmine API 連線
```bash
curl -X GET http://your-nas-ip:8000/status
# 檢查 redmine_connection: true
```

### 3. Email 服務測試
```bash
curl -X POST http://your-nas-ip:8000/test-email \
     -H "Content-Type: application/json" \
     -d '{"to": "test@gogopeaks.com"}'
```

### 4. 報表生成測試
```bash
curl -X POST http://your-nas-ip:8000/generate-report \
     -H "Content-Type: application/json" \
     -d '{"force": true}'
```

### 5. n8n 整合測試
在 n8n 1.107.4 中執行工作流程並檢查回應

## 🔍 故障排除

### 常見問題

1. **Redmine 6.0.6 API 錯誤**
   - 檢查 API Key 是否正確
   - 確認 Redmine URL 格式
   - 驗證使用者權限

2. **MailPlus 寄送失敗**
   - 檢查 SMTP 設定
   - 驗證帳戶密碼
   - 確認防火牆規則

3. **n8n 1.107.4 連接問題**
   - 檢查容器網路設定
   - 驗證 API 端點
   - 查看 n8n 錯誤日誌

### 日誌位置

```
/volume1/docker/redmine-report/logs/
├── app.log           # 應用程式日誌
├── email.log         # Email 發送日誌
├── redmine.log       # Redmine API 日誌
└── n8n-integration.log # n8n 整合日誌
```

**🎯 專為你的環境優化 - Synology + n8n 1.107.4 + Redmine 6.0.6 + MailPlus**
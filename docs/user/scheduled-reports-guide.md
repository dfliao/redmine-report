# Redmine 報表自動排程使用指南

## 概述

系統提供多種方式來自動定期發送Redmine報表，包括手動觸發、系統排程和n8n工作流程整合。

## 可用的排程方式

### 1. 立即手動執行 (測試用)

#### A. 透過指令腳本
```bash
# 在容器內執行
docker exec -it redmine-report-service python /app/scripts/send_scheduled_reports.py

# 或在主機上執行
cd /volume1/ai-stack2/redmine-report
python scripts/send_scheduled_reports.py
```

#### B. 透過API呼叫
```bash
# 發送報表一
curl -X POST "http://192.168.0.222:3003/api/send-report" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": 1,
    "admin_username": "admin",
    "admin_password": "your_password"
  }'

# 發送報表二  
curl -X POST "http://192.168.0.222:3003/api/send-report" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": 2,
    "admin_username": "admin", 
    "admin_password": "your_password"
  }'

# 發送報表三
curl -X POST "http://192.168.0.222:3003/api/send-report" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": 3,
    "admin_username": "admin",
    "admin_password": "your_password"
  }'
```

### 2. Synology DSM 任務排程器 (推薦)

#### 設定步驟：
1. 登入DSM管理界面
2. 開啟「控制台」→「任務排程器」
3. 建立新的「使用者定義的指令碼」任務
4. 設定執行時間和頻率

#### 任務設定範例：

**每日報表 (報表一、二)**
```bash
# 任務名稱：Daily Redmine Reports
# 執行時間：每天上午 9:00
# 指令：
docker exec redmine-report-service python /app/scripts/send_scheduled_reports.py
```

**週報 (報表三)**
```bash
# 任務名稱：Weekly Special Project Report  
# 執行時間：每週一上午 9:00
# 指令：
curl -X POST "http://localhost:3003/api/send-report" \
  -H "Content-Type: application/json" \
  -d '{"report_type": 3, "admin_username": "admin", "admin_password": "your_password"}'
```

### 3. Docker Compose 環境變數配置

在 `.env` 檔案中設定：

```bash
# 排程設定
SCHEDULE_CRON=0 9 * * *           # 每天上午9點執行 (cron格式)

# 報表自動發送開關
REPORT1_AUTO_SEND=true            # 啟用報表一自動發送
REPORT2_AUTO_SEND=true            # 啟用報表二自動發送  
REPORT3_AUTO_SEND=false           # 停用報表三自動發送 (手動或週報)

# 自訂收件者 (可選，留空則發送給所有Redmine使用者)
REPORT1_RECIPIENTS=manager@company.com,admin@company.com
REPORT2_RECIPIENTS=dev-team@company.com
REPORT3_RECIPIENTS=executives@company.com
```

### 4. n8n 工作流程整合

#### 建立n8n工作流程：
1. **Cron節點**: 設定觸發時間
2. **HTTP Request節點**: 呼叫報表API
3. **條件節點**: 處理成功/失敗情況

#### 工作流程範例：
```json
{
  "nodes": [
    {
      "name": "每日報表觸發器",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "rule": {
          "interval": [
            {"field": "hour", "value": 9},
            {"field": "minute", "value": 0}
          ]
        }
      }
    },
    {
      "name": "發送報表一",
      "type": "n8n-nodes-base.httpRequest", 
      "parameters": {
        "url": "http://192.168.0.222:3003/api/send-report",
        "method": "POST",
        "body": {
          "report_type": 1,
          "admin_username": "admin",
          "admin_password": "password"
        }
      }
    }
  ]
}
```

## 排程時間建議

### 報表一 (議題進度統計)
- **建議頻率**: 每日
- **建議時間**: 上午 9:00
- **適用對象**: 專案經理、團隊成員

### 報表二 (完成日期異動)
- **建議頻率**: 每日  
- **建議時間**: 上午 9:00 或下午 5:00
- **適用對象**: 專案經理、品管人員

### 報表三 (專項用專案)
- **建議頻率**: 每週一次
- **建議時間**: 週一上午 9:00
- **適用對象**: 高階主管、專案負責人

### 報表四 (甘特圖)
- **建議頻率**: 每週一次
- **建議時間**: 週一上午 10:00
- **適用對象**: 工程部門、施工團隊

## 監控和日誌

### 查看執行日誌
```bash
# 檢查容器日誌
docker logs redmine-report-service

# 檢查排程腳本日誌
tail -f /tmp/redmine_scheduled_reports.log

# 檢查Docker Compose服務狀態
docker-compose ps
```

### 常見問題排解

#### 問題1: 報表沒有發送
**檢查項目**:
- SMTP設定是否正確
- 管理員帳號密碼是否有效
- Redmine API連線是否正常

#### 問題2: 收件者清單為空
**解決方案**:
- 檢查Redmine使用者是否有Email地址
- 確認`REPORT*_RECIPIENTS`環境變數設定

#### 問題3: 排程沒有執行
**解決方案**:
- 檢查cron語法是否正確
- 確認DSM任務排程器設定
- 檢查容器運作狀態

## 測試和驗證

### 測試排程功能
```bash
# 測試單一報表發送
docker exec redmine-report-service python -c "
import asyncio
from src.main.python.core.settings import Settings
from src.main.python.services.report_generator import ReportGenerator
from src.main.python.services.redmine_service import RedmineService
from src.main.python.services.email_service import EmailService

async def test():
    settings = Settings()
    redmine_service = RedmineService(settings)
    email_service = EmailService(settings)  
    report_generator = ReportGenerator(settings, redmine_service, email_service)
    result = await report_generator.generate_and_send_report1()
    print('Test result:', result)

asyncio.run(test())
"
```

### 驗證排程設定
```bash
# 檢查環境變數
docker exec redmine-report-service env | grep REPORT

# 測試API連線
curl -X GET "http://192.168.0.222:3003/health"
```

## 安全性注意事項

1. **密碼安全**: 不要在指令中明文寫入密碼，使用環境變數
2. **API存取**: 確保只有授權的系統可以存取報表API
3. **日誌管理**: 定期清理日誌檔案，避免磁碟空間不足
4. **網路安全**: 確保SMTP和Redmine連線使用加密協定

---

**提示**: 建議先在測試環境驗證排程功能正常後，再部署到生產環境使用。
# 每日自動報表寄送設定指南

## 🎯 概述

本指南說明如何設定每日自動寄送Redmine報表，包括過濾參數設定和排程配置。

## 📧 可用報表類型

### 報表一：議題狀態統計
- **內容**: 14天內進行中議題數量統計（按被分派者和狀態）
- **API**: `/send-email?report_type=1`
- **適用**: 每日追蹤團隊工作狀況

### 報表二：完工議題清單  
- **內容**: 14天內完工進行中議題清單
- **API**: `/send-email?report_type=2`  
- **適用**: 每日檢視完成項目

### 報表三：專案週報
- **內容**: 專案進度統計和重點議題
- **API**: `/send-email?report_type=3`
- **適用**: 週一寄送週報

### 報表四：甘特圖（暫不支援email）
- **內容**: 施工安裝進度甘特圖
- **網頁**: `/report4` 
- **適用**: 線上查看專案時程

## 🔧 排程設定方式

### 方式一：Synology DSM 任務排程器（推薦）

#### 設定步驟：
1. **進入DSM控制台** → 任務排程器
2. **建立新任務** → 排定的任務 → 使用者定義的指令碼
3. **一般設定**：
   - 任務名稱：`每日Redmine報表`
   - 使用者：選擇有權限的使用者
   - 已啟用：勾選

4. **排程設定**：
   ```
   每日執行時間: 08:00 AM
   重複: 每天
   ```

5. **任務設定 - 指令碼**：
   ```bash
   # 報表一 - 每日 08:00
   curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14"
   
   # 可加入多個報表（不同時間執行）：
   sleep 300  # 等5分鐘
   curl -X POST "http://localhost:3003/send-email?report_type=2&auto_send=true&days=14"
   ```

#### 進階排程範例：
```bash
#!/bin/bash

# 每日報表一（08:00）
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14" \
     -H "Content-Type: application/json"

# 等待5分鐘後寄送報表二
sleep 300
curl -X POST "http://localhost:3003/send-email?report_type=2&auto_send=true&days=14" \
     -H "Content-Type: application/json"

# 週一才寄送報表三（週報）
if [ $(date +%u) -eq 1 ]; then
    sleep 300
    curl -X POST "http://localhost:3003/send-email?report_type=3&auto_send=true&days=7" \
         -H "Content-Type: application/json"
fi
```

### 方式二：n8n 工作流程

#### 工作流程節點設定：

1. **Cron 節點**（觸發器）：
   ```
   Cron表達式: 0 8 * * *  # 每日 08:00
   時區: Asia/Taipei
   ```

2. **HTTP Request 節點**：
   ```json
   {
     "method": "POST",
     "url": "http://redmine-report:3003/send-email",
     "body": {
       "report_type": "1",
       "auto_send": "true",
       "days": "14"
     }
   }
   ```

3. **條件節點**（可選）：
   ```javascript
   // 只在工作日執行
   const day = new Date().getDay();
   return day >= 1 && day <= 5;  // 週一到週五
   ```

### 方式三：Docker Compose 環境變數

在 `docker-compose.yml` 中已有相關設定：

```yaml
environment:
  # 排程設定
  - SCHEDULE_CRON=${SCHEDULE_CRON:-0 8 * * 1}  # 每週一 08:00
  
  # 自動寄送設定
  - REPORT1_AUTO_SEND=${REPORT1_AUTO_SEND:-true}
  - REPORT2_AUTO_SEND=${REPORT2_AUTO_SEND:-true}  
  - REPORT3_AUTO_SEND=${REPORT3_AUTO_SEND:-false}
  
  # 自訂收件者
  - REPORT1_RECIPIENTS=${REPORT1_RECIPIENTS:-}
  - REPORT2_RECIPIENTS=${REPORT2_RECIPIENTS:-}
  - REPORT3_RECIPIENTS=${REPORT3_RECIPIENTS:-}
```

## ⚙️ 過濾參數設定

### 基本參數

| 參數 | 說明 | 範例 | 預設值 |
|------|------|------|--------|
| `report_type` | 報表類型 (1,2,3) | `report_type=1` | 無 |
| `auto_send` | 自動寄送模式 | `auto_send=true` | false |
| `days` | 資料範圍天數 | `days=14` | 14 |

### 進階過濾參數

#### 報表一和二通用：
```bash
# 基本API調用
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14"

# 指定特定專案
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14&project_filter=網站開發"

# 指定特定被分派者
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14&assignee_filter=張三"

# 指定追蹤標籤
curl -X POST "http://localhost:3003/send-email?report_type=2&auto_send=true&days=14&tracker_filter=功能"
```

#### 自訂收件者：
```bash
# 使用環境變數設定的收件者
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true"

# 臨時指定收件者（如支援）
curl -X POST "http://localhost:3003/send-email" \
     -H "Content-Type: application/json" \
     -d '{
       "report_type": 1,
       "auto_send": true, 
       "custom_recipients": ["manager@company.com", "team@company.com"]
     }'
```

## 🎯 建議排程配置

### 每日報表排程：
```bash
# 08:00 - 報表一（議題狀態統計）
0 8 * * * curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=14"

# 08:05 - 報表二（完工議題清單） 
5 8 * * * curl -X POST "http://localhost:3003/send-email?report_type=2&auto_send=true&days=14"

# 08:00 週一 - 報表三（週報）
0 8 * * 1 curl -X POST "http://localhost:3003/send-email?report_type=3&auto_send=true&days=7"
```

### 不同時間的報表：
```bash
# 早上 08:00 - 昨日完工議題
curl -X POST "http://localhost:3003/send-email?report_type=2&auto_send=true&days=1"

# 下午 17:00 - 今日議題狀態
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=1"
```

## 📋 測試和驗證

### 手動測試API：
```bash
# 測試報表生成（不寄送）
curl -X GET "http://localhost:3003/report1?days=14"

# 測試郵件寄送
curl -X POST "http://localhost:3003/send-email?report_type=1&auto_send=true&days=1"
```

### 檢查排程狀態：
```bash
# 檢查 Docker 容器狀態
docker logs redmine-report-service

# 檢查排程任務
# 在 Synology DSM → 任務排程器中查看執行記錄
```

## 🛠️ 故障排除

### 常見問題：

1. **郵件寄送失敗**
   - 檢查 SMTP 設定
   - 確認網路連線
   - 查看容器日誌

2. **排程未執行**
   - 確認任務排程器設定
   - 檢查使用者權限
   - 驗證API端點可達性

3. **報表內容為空**
   - 檢查 Redmine API 連線
   - 確認過濾條件是否過於嚴格
   - 驗證日期範圍設定

### 日誌查看：
```bash
# 查看應用程式日誌
docker logs redmine-report-service -f

# 查看特定時間的日誌
docker logs redmine-report-service --since "2024-01-01T08:00:00"
```

## 🎯 最佳實務

1. **時間設定**：避開系統維護時間
2. **收件者管理**：使用群組信箱避免個人信箱異動
3. **錯誤通知**：設定失敗時的通知機制
4. **備份排程**：定期備份排程設定
5. **測試驗證**：新排程上線前先進行測試

---

**完成設定後，您將擁有自動化的每日Redmine報表系統！**
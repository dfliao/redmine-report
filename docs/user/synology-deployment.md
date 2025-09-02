# Synology NAS 部署指南

本文件說明如何在 Synology NAS 的 Container Manager 中部署 Redmine Report Generator。

## 📋 系統需求

- **Synology NAS**: DSM 7.0 或更高版本
- **Container Manager**: 已安裝並啟用
- **Redmine**: 6.0.6 版本 (已測試相容)
- **記憶體**: 建議至少 512MB 可用記憶體
- **儲存空間**: 建議至少 1GB 可用空間

## 🚀 部署步驟

### 1. 準備專案檔案

1. 將整個專案複製到 Synology NAS 的共享資料夾
2. 建議路径：`/volume1/ai-stack2/redmine-report/`

### 2. 設定環境變數

複製並編輯環境變數檔案：

```bash
# 在 NAS 上執行
cd /volume1/ai-stack2/redmine-report/
cp .env.example .env
nano .env
```

重要設定項目：

```env
# Redmine 6.0.6 配置
REDMINE_URL=http://your-redmine-server.local:3000
REDMINE_API_KEY=your_api_key_from_redmine_6_0_6

# Email 設定 (Gmail 範例)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password

# 報表設定
REPORT_DAYS=14
TIMEZONE=Asia/Taipei
SCHEDULE_CRON=0 8 * * 1  # 每週一早上8點
```

### 3. 使用 Container Manager 部署

#### 方法 A: Docker Compose (推薦)

1. 開啟 **Container Manager**
2. 點選 **專案** → **建立**
3. 設定：
   - **專案名稱**: `redmine-report`
   - **路徑**: `/volume1/ai-stack2/redmine-report`
   - **來源**: `建立 docker-compose.yml`
4. 上傳或貼上 `docker-compose.yml` 內容
5. 點選 **建立**

#### 方法 B: 單一容器部署

1. 開啟 **Container Manager**
2. 點選 **容器** → **建立**
3. 使用以下設定：

**基本設定:**
- **映像**: 先建置映像或使用預建映像
- **容器名稱**: `redmine-report`
- **自動重新啟動**: 是

**連接埠設定:**
- **本機連接埠**: 8000
- **容器連接埠**: 8000
- **類型**: TCP

**環境變數**: 將 `.env` 檔案內容逐一新增

**磁碟區設定:**
```
本機路径                              容器路径                        類型
/volume1/ai-stack2/redmine-report/output    /app/output                    讀寫
/volume1/ai-stack2/redmine-report/.env      /app/.env                      唯讀
```

### 4. 驗證部署

部署完成後，驗證服務是否正常運行：

```bash
# 檢查健康狀態
curl http://your-nas-ip:8000/health

# 檢查服務狀態
curl http://your-nas-ip:8000/status

# 手動觸發報表生成測試
curl -X POST http://your-nas-ip:8000/generate-report
```

## ⚙️ Synology 特殊配置

### 1. 網路設定

如果 Redmine 也部署在同一台 NAS 上：

```yaml
# docker-compose.yml 中加入
networks:
  synology-bridge:
    external: true
```

### 2. 記憶體最佳化

針對 Synology NAS 的記憶體限制：

```yaml
# 已在 docker-compose.yml 中設定
deploy:
  resources:
    limits:
      memory: 256M    # 適合 NAS 的記憶體限制
      cpus: '0.8'     # 保留 CPU 資源給其他服務
```

### 3. 日誌管理

避免日誌檔案過大：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # 單檔最大 10MB
    max-file: "3"     # 保留最多 3 個日誌檔案
```

### 4. 資料持久化

確保輸出檔案保存在 NAS 上：

```yaml
volumes:
  - ./output:/app/output:rw
  - ./logs:/app/logs:rw  # 可選：日誌持久化
```

## 🔧 n8n 整合 (在 Synology 上)

如果你也在 Synology 上運行 n8n：

### 1. n8n 工作流程設定

**HTTP Request 節點設定:**

```json
{
  "method": "POST",
  "url": "http://redmine-report:8000/generate-report",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "force": true
  }
}
```

**注意**: 使用容器名稱 `redmine-report` 作為主機名稱

### 2. 排程設定

在 n8n 中建立排程工作流程：

1. **Cron Trigger**: `0 8 * * 1` (每週一 8:00 AM)
2. **HTTP Request**: 調用報表生成 API
3. **Conditional**: 檢查回應狀態
4. **Notification**: 發送結果通知到 Slack/Teams

## 📊 監控與維護

### 1. 檢查容器狀態

在 Container Manager 中：
- 查看 **容器** 頁面的運行狀態
- 檢查 **日誌** 頁面的執行日誌
- 監控 **效能** 頁面的資源使用情況

### 2. 查看輸出檔案

生成的報表會儲存在：
```
/volume1/ai-stack2/redmine-report/output/
├── report_YYYY-MM-DD.xlsx
└── logs/
    └── app.log
```

### 3. 故障排除

**常見問題:**

1. **記憶體不足**
   - 減少其他運行中的容器
   - 或調整記憶體限制設定

2. **網路連線問題**
   - 檢查 Redmine 伺服器是否可達
   - 確認防火牆設定

3. **權限問題**
   - 檢查共享資料夾的讀寫權限
   - 確認 Docker 有權限存取資料夾

### 4. 定期維護

建議定期執行：

```bash
# 清理舊的報表檔案 (保留最近30天)
find /volume1/ai-stack2/redmine-report/output -name "*.xlsx" -mtime +30 -delete

# 檢查容器映像更新
docker pull your-registry/redmine-report:latest
docker-compose up -d
```

## 🔒 安全性建議

1. **API Key 保護**: 將 Redmine API Key 存放在安全的環境變數中
2. **網路隔離**: 使用 Docker 網路隔離容器
3. **資料加密**: 啟用 NAS 的資料夾加密功能
4. **定期備份**: 定期備份配置檔案和輸出檔案
5. **存取控制**: 限制 API 端點的存取來源

## 📞 支援

如有部署問題，請檢查：

1. Container Manager 的日誌記錄
2. 應用程式的 `/app/logs/` 目錄
3. Docker Compose 的服務狀態

**🎯 Template by Chang Ho Chien | HC AI 說人話channel | v1.0.0**
# 🚀 Synology DS920+ 部署指南

## 📋 前置條件檢查

### 1. 系統需求
- ✅ Synology DS920+ (或相容機種)
- ✅ DSM 7.0 或更高版本
- ✅ Container Manager 已安裝
- ✅ 至少 512MB 可用 RAM
- ✅ SSH 連線能力

### 2. 網路需求
- ✅ Redmine 伺服器網路連線
- ✅ SMTP 伺服器連線 (Email 發送)
- ✅ Port 3003 可用於 Web 介面

## 🔧 第一步：環境準備

### 1. SSH 登入 DS920+
```bash
ssh admin@your-ds920-ip
```

### 2. 建立專案目錄
```bash
# 進入現有 ai-stack2 目錄
cd /volume1/ai-stack2

# 下載專案 (如果還沒有)
git clone https://github.com/dfliao/redmine-report.git
cd redmine-report

# 建立輸出目錄
mkdir -p output
chmod 755 output
```

### 3. 設定環境變數
```bash
# 複製環境變數範本
cp .env.example .env

# 編輯配置
nano .env
```

## ⚙️ 第二步：設定 .env 檔案

**必填項目：**
```bash
# Redmine 配置
REDMINE_URL=http://your-redmine.example.com
REDMINE_API_KEY=your_api_key_here

# Email 配置 (MailPlus Server)
SMTP_HOST=your-synology-nas.local
SMTP_USERNAME=GOPEAK@mail.gogopeaks.com
SMTP_PASSWORD=your_mailplus_password  
EMAIL_FROM=GOPEAK@mail.gogopeaks.com
```

**推薦設定：**
```bash
# 效能調整
MAX_WORKERS=2
MEMORY_LIMIT=256M
CPU_LIMIT=0.8

# 日誌等級
DEBUG=false
LOG_LEVEL=INFO
```

## 🐳 第三步：Container Manager 部署

### 1. 開啟 Container Manager
- DSM 主選單 → Container Manager

### 2. 建立專案
- 點擊「專案」→「新增」
- 專案名稱：`redmine-report`
- 路徑選擇：`/volume1/ai-stack2/redmine-report`
- 來源：選擇「建立 docker-compose.yml」

### 3. 上傳 docker-compose.yml
```yaml
version: '3.8'

services:
  redmine-report:
    build: .
    container_name: redmine-report-service
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "3003:3003"
    volumes:
      - ./output:/app/output:rw
      - ./src/main/resources:/app/src/main/resources:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; r = requests.get('http://localhost:3003/health', timeout=5); assert r.status_code == 200"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '0.8'
          memory: 256M
        reservations:
          cpus: '0.2'
          memory: 128M
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 啟動服務
- 點擊「建置」→ 等待 Docker 映像建構完成
- 建構完成後點擊「啟動」

## 🔍 第四步：驗證部署

### 1. 檢查容器狀態
```bash
# 檢查容器是否運行
docker ps | grep redmine-report

# 檢查日誌
docker logs redmine-report-service
```

### 2. 測試 Web 介面
- 瀏覽器開啟：`http://your-ds920-ip:3003`
- 應該看到 Redmine 報表系統首頁

### 3. 測試 API 端點
```bash
# 健康檢查
curl http://your-ds920-ip:3003/health

# 服務狀態
curl http://your-ds920-ip:3003/status

# 手動觸發報表
curl -X POST http://your-ds920-ip:3003/generate-report
```

## 📧 第五步：Email 測試

### 1. MailPlus Server 設定
- DSM → MailPlus Server
- 確認 SMTP 服務已啟用
- 建立專用帳號：`GOPEAK@mail.gogopeaks.com`

### 2. 測試 Email 發送
```bash
# 進入容器測試
docker exec -it redmine-report-service python -m src.main.python.core.main --standalone
```

## 🔧 第六步：排程設定

### 1. 確認排程配置
- 編輯 `.env` 檔案中的 `SCHEDULE_CRON`
- 預設：`0 8 * * 1` (每週一上午8點)

### 2. 排程選項：
```bash
# 每日上午 8 點
SCHEDULE_CRON=0 8 * * *

# 每週一上午 8 點
SCHEDULE_CRON=0 8 * * 1

# 每小時執行
SCHEDULE_CRON=0 * * * *
```

## 🚨 故障排除

### 常見問題：

**1. 容器無法啟動**
```bash
# 檢查日誌
docker logs redmine-report-service

# 檢查配置
docker-compose config
```

**2. 無法連線到 Redmine**
```bash
# 測試網路連線
curl -I $REDMINE_URL

# 檢查 API Key
curl -H "X-Redmine-API-Key: $REDMINE_API_KEY" $REDMINE_URL/issues.json
```

**3. Email 發送失敗**
```bash
# 檢查 SMTP 設定
telnet your-synology-nas.local 587

# 檢查 MailPlus 狀態
# DSM → MailPlus Server → 狀態
```

**4. 記憶體不足**
```bash
# 調整記憶體限制
# 編輯 docker-compose.yml
memory: 512M  # 增加到 512MB
```

## 📊 監控與維護

### 1. 日常檢查
- Container Manager → 監控容器狀態
- 檢查 `/volume1/ai-stack2/redmine-report/output` 報表輸出

### 2. 日誌管理
```bash
# 檢視即時日誌
docker logs -f redmine-report-service

# 日誌輪替已自動配置 (10MB, 3 個檔案)
```

### 3. 系統更新
```bash
# 更新程式碼
cd /volume1/ai-stack2/redmine-report
git pull origin master

# 重新建置
docker-compose build --no-cache
docker-compose up -d
```

## 🎯 部署檢查清單

- [ ] SSH 連線正常
- [ ] 專案目錄已建立
- [ ] `.env` 檔案已正確設定
- [ ] Container Manager 專案已建立
- [ ] 容器成功啟動
- [ ] Web 介面可正常存取 (port 3003)
- [ ] API 端點回應正常
- [ ] Email 功能測試通過
- [ ] 排程設定確認
- [ ] 報表輸出目錄權限正確

## 📞 支援資訊

**問題回報：**
- GitHub: https://github.com/dfliao/redmine-report/issues

**相關文件：**
- README.md - 專案概述
- CLAUDE.md - 開發規則
- docker-compose.yml - 容器配置

**建議監控：**
- 容器運行狀態
- 記憶體使用量
- 日誌錯誤訊息
- Email 發送成功率
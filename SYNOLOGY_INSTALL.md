# Synology DS920+ 完整安裝指南

## 📋 安裝前準備清單

### 系統要求
- ✅ Synology DS920+ 
- ✅ DSM 7.0+ 已安裝
- ✅ Container Manager 套件已安裝
- ✅ 可用記憶體：1GB+
- ✅ 可用空間：2GB+

### 必要資訊收集
在開始安裝前，請準備以下資訊：

```
🔹 Redmine 伺服器資訊：
- Redmine URL: http://your-redmine-server:3000
- API Key: (從 Redmine 管理介面取得)

🔹 Synology MailPlus 資訊：
- SMTP Host: your-synology-nas.local (或IP位址)
- Email: GOPEAK@mail.gogopeaks.com
- Password: (MailPlus 帳戶密碼)

🔹 n8n 資訊 (如果已安裝)：
- n8n URL: http://your-nas-ip:5678
```

## 🚀 安裝步驟

### 步驟 1: 建立專案目錄

1. **透過 File Station：**
   - 開啟 File Station
   - 建立資料夾：`ai-stack2/redmine-report`
   - 路徑：`/volume1/ai-stack2/redmine-report/`

2. **透過 SSH (進階用戶)：**
```bash
ssh admin@your-ds920-ip
sudo mkdir -p /volume1/ai-stack2/redmine-report
cd /volume1/ai-stack2/redmine-report
```

### 步驟 2: 下載專案檔案

**方法 A: 使用 git (推薦)**
```bash
# SSH 登入 DS920+
cd /volume1/ai-stack2
git clone https://github.com/dfliao/redmine-report.git
```

**方法 B: 手動上傳**
1. 在電腦下載：https://github.com/dfliao/redmine-report/archive/refs/heads/master.zip
2. 解壓縮後透過 File Station 上傳到 `/volume1/ai-stack2/redmine-report/`

### 步驟 3: 設定環境變數

1. **複製環境變數範本：**
```bash
cd /volume1/ai-stack2/redmine-report
cp .env.example .env
```

2. **編輯 .env 檔案：**
```bash
# 使用文字編輯器編輯
nano .env
```

3. **完整 .env 配置範例：**
```env
# ================================
# Redmine 6.0.6 Configuration
# ================================
REDMINE_URL=http://192.168.1.100:3000
REDMINE_API_KEY=abcd1234567890efgh
REDMINE_VERSION=6.0.6

# ================================
# Synology MailPlus Server
# ================================
SMTP_HOST=192.168.1.50
SMTP_PORT=587
SMTP_USERNAME=GOPEAK@mail.gogopeaks.com
SMTP_PASSWORD=your_mailplus_password
EMAIL_FROM=GOPEAK@mail.gogopeaks.com
EMAIL_USE_TLS=true

# ================================
# 報表設定
# ================================
REPORT_DAYS=14
TIMEZONE=Asia/Taipei
SCHEDULE_CRON=0 8 * * 1

# ================================
# Synology DS920+ 最佳化
# ================================
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
DEBUG=false
```

### 步驟 4: 使用 Container Manager 部署

1. **開啟 Container Manager**
2. **建立專案：**
   - 點選 **專案** → **建立**
   - 專案名稱：`redmine-report`
   - 路徑：`/volume1/ai-stack2/redmine-report`

3. **設定 Docker Compose：**
   - 選擇 **建立 docker-compose.yml**
   - 貼上專案中的 docker-compose.yml 內容

4. **調整 DS920+ 資源設定：**

在 docker-compose.yml 中確認以下設定適合 DS920+：

```yaml
deploy:
  resources:
    limits:
      cpus: '0.8'        # DS920+ CPU 限制
      memory: 256M       # DS920+ 記憶體限制
    reservations:
      cpus: '0.1'
      memory: 64M

logging:
  driver: "json-file"
  options:
    max-size: "10m"      # 日誌大小限制
    max-file: "3"
```

5. **建立並啟動專案**
   - 點選 **建立**
   - 等待容器下載和啟動

### 步驟 5: 驗證部署

1. **檢查容器狀態：**
   - 在 Container Manager 中查看 `redmine-report` 容器
   - 狀態應該顯示為 **執行中**

2. **測試 API 連接：**
```bash
# 替換 192.168.1.50 為你的 DS920+ IP
curl http://192.168.1.50:8000/health
```

預期回應：
```json
{"status":"healthy","version":"1.0.0"}
```

3. **檢查服務狀態：**
```bash
curl http://192.168.1.50:8000/status
```

4. **測試報表生成：**
```bash
curl -X POST http://192.168.1.50:8000/generate-report \
     -H "Content-Type: application/json" \
     -d '{"force": true}'
```

### 步驟 6: n8n 1.107.4 整合設定

如果你有安裝 n8n，建立以下工作流程：

1. **HTTP Request 節點設定：**
```json
{
  "method": "POST",
  "url": "http://redmine-report:8000/generate-report",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "force": true
  },
  "options": {
    "timeout": 300000
  }
}
```

2. **Cron 觸發器：**
```
0 8 * * 1  # 每週一早上8點
```

## 🔧 常見問題排除

### 問題 1: 容器無法啟動

**檢查步驟：**
1. 查看 Container Manager 日誌
2. 檢查 .env 檔案格式
3. 確認埠號 8000 沒有被佔用

**解決方案：**
```bash
# 檢查埠號佔用
sudo netstat -tulpn | grep :8000

# 重啟容器
docker-compose restart
```

### 問題 2: 無法連接 Redmine

**檢查步驟：**
1. 確認 Redmine URL 可從 DS920+ 存取
2. 驗證 API Key 正確性
3. 檢查防火牆設定

**測試連線：**
```bash
# 從 DS920+ 測試 Redmine 連線
curl -H "X-Redmine-API-Key: YOUR_API_KEY" \
     http://your-redmine-server:3000/issues.json?limit=1
```

### 問題 3: Email 發送失敗

**檢查步驟：**
1. 確認 MailPlus Server 設定
2. 檢查 SMTP 帳戶密碼
3. 驗證網路連線

**測試 SMTP：**
```bash
# 測試 SMTP 連線
telnet your-synology-nas.local 587
```

### 問題 4: 記憶體不足

**DS920+ 最佳化設定：**
```yaml
# 在 docker-compose.yml 中調整
deploy:
  resources:
    limits:
      memory: 128M    # 降低記憶體限制
      cpus: '0.5'     # 降低 CPU 使用
```

## 📊 DS920+ 效能監控

### 監控指標
- **CPU 使用率**: 應該 < 50%
- **記憶體使用**: 應該 < 256MB
- **磁碟 I/O**: 監控輸出檔案寫入

### 監控命令
```bash
# 查看容器資源使用
docker stats redmine-report-service

# 查看系統資源
htop

# 查看磁碟使用
df -h /volume1/ai-stack2/redmine-report/
```

## 🎯 完成安裝確認

安裝完成後，你應該能夠：

✅ 在 Container Manager 看到執行中的容器
✅ 透過瀏覽器存取 http://DS920-IP:8000/health
✅ 收到測試報表 Email
✅ 在 n8n 中成功觸發報表生成

## 📞 技術支援

如果遇到問題：

1. **查看日誌：**
   ```bash
   docker logs redmine-report-service
   ```

2. **檢查設定：**
   ```bash
   cat /volume1/ai-stack2/redmine-report/.env
   ```

3. **重啟服務：**
   ```bash
   cd /volume1/ai-stack2/redmine-report
   docker-compose restart
   ```

**🎯 專為 Synology DS920+ 最佳化的完整安裝指南**

---

> 💡 **提示**: DS920+ 的 4GB 記憶體對於這個應用來說綽綽有餘，但建議監控資源使用情況以確保系統穩定性。
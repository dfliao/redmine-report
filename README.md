# Redmine Report Generator

🚀 Automated Redmine reporting system with email delivery, designed for container deployment (Docker, n8n, Synology NAS).

## 📊 Features

- **雙表格報表系統**：
  - 📈 **統計表格**：14天內進行中議題數量統計（依被分派者和狀態分類）
  - 📋 **清單表格**：14天內完工進行中議題詳細清單
- **📧 自動 Email 發送**：寄送給所有任務議題的被分派者
- **🐳 容器化部署**：支援 Docker、Synology Container Manager
- **🔗 n8n 整合**：提供 API 端點供 n8n 工作流程調用
- **⏰ 排程執行**：支援 cron 格式的定時執行

## 🏗️ 專案結構

```
redmine-report/
├── 📋 CLAUDE.md              # Claude Code 操作規則
├── 📖 README.md              # 專案說明文件
├── 🐳 Dockerfile             # 容器化配置
├── 🐙 docker-compose.yml     # Docker Compose 設定
├── 📦 requirements.txt       # Python 相依套件
├── 🚫 .gitignore             # Git 忽略規則
├── 📁 src/                   # 原始碼目錄
│   ├── main/python/          # Python 應用程式碼
│   │   ├── core/             # 核心商業邏輯
│   │   ├── services/         # 服務層 (Redmine API, Email)
│   │   ├── models/           # 資料模型
│   │   └── utils/            # 工具函式
│   └── test/                 # 測試程式碼
├── 📁 docs/                  # 文件目錄
├── 📁 output/                # 報表輸出目錄
└── 🔧 tools/                 # 開發工具

```

## 🚀 快速開始

### 1. 使用 Docker Compose (推薦)

```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 編輯配置檔案
nano .env

# 3. 啟動服務
docker-compose up -d

# 4. 檢查服務狀態
curl http://localhost:8000/health
```

### 2. 手動觸發報表生成

```bash
# 透過 API 觸發 (適用於 n8n)
curl -X POST http://localhost:8000/generate-report

# 檢查服務狀態
curl http://localhost:8000/status
```

### 3. 本地開發

```bash
# 安裝相依套件
pip install -r requirements.txt

# 設定環境變數
export REDMINE_URL="http://your-redmine.com"
export REDMINE_API_KEY="your_api_key"

# 執行一次性報表生成
python -m src.main.python.core.main --standalone

# 或啟動 API 服務器
python -m src.main.python.core.main
```

## ⚙️ 配置說明

### 環境變數

| 變數名 | 說明 | 範例 |
|--------|------|------|
| `REDMINE_URL` | Redmine 伺服器網址 | `http://redmine.company.com` |
| `REDMINE_API_KEY` | Redmine API 金鑰 | `abc123...` |
| `SMTP_HOST` | SMTP 伺服器 | `smtp.gmail.com` |
| `SMTP_USERNAME` | 電子郵件帳號 | `reports@company.com` |
| `SMTP_PASSWORD` | 電子郵件密碼 | `app_password` |
| `REPORT_DAYS` | 報表天數範圍 | `14` |
| `SCHEDULE_CRON` | 排程設定 (cron 格式) | `0 8 * * 1` (每週一早上8點) |

## 🔧 n8n 整合

### 使用 HTTP Request 節點

```javascript
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

### 排程觸發範例

1. **Cron 節點**：設定為每週一早上 8:00 執行
2. **HTTP Request 節點**：調用 `/generate-report` 端點
3. **條件判斷節點**：檢查回應狀態
4. **通知節點**：發送執行結果通知

## 📊 報表內容

### 第一個表格：議題數量統計
- **列**：被分派者姓名
- **欄**：議題狀態（擬定中、執行中、待審核、修正中、已回應、已完成、暫停、取消）
- **內容**：各狀態議題數量

### 第二個表格：議題詳細清單
- **追蹤標籤**：議題追蹤編號
- **狀態**：當前狀態
- **優先權**：議題優先等級
- **主旨**：議題標題
- **被分派者**：負責人員
- **完工日期**：預計完成日期
- **開始日期**：議題開始日期
- **更新日期**：最後更新時間

## 🐳 Synology NAS 部署

1. 開啟 **Container Manager**
2. 建立專案，上傳 `docker-compose.yml`
3. 設定環境變數檔案 `.env`
4. 啟動容器服務
5. 檢查容器健康狀態

## 🛠️ 開發指南

請先閱讀 `CLAUDE.md` 了解專案開發規則：

- ✅ 遵循 CLAUDE.md 中的所有規範
- ✅ 程式碼放在適當的模組結構中
- ✅ 每完成一個功能就提交 commit
- ✅ 使用 Task agents 處理長時間操作
- ✅ 避免建立重複功能的檔案

## 📝 授權與致謝

**🎯 Template by Chang Ho Chien | HC AI 說人話channel | v1.0.0**  
📺 Tutorial: https://youtu.be/8Q1bRZaHH24
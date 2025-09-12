# schedule_reports.sh 自動排程設定指南

## 📋 概述

`schedule_reports.sh` 是一個全自動化的 Redmine 報表發送腳本，支援：
- 每日工作日報表自動發送
- 週報自動發送
- 月報自動發送（可選）
- 完整的日誌記錄
- 錯誤處理和重試機制

## 🎯 預設排程時間

| 時間 | 報表 | 頻率 | 資料範圍 |
|------|------|------|----------|
| **08:00** | 報表一、二、五 | 每工作日 | 14天 |
| **08:30** | 報表三（週報） | 每週一 | 7天 |
| **09:00** | 報表三（月報） | 每月第一個工作日 | 30天 |
| **23:59** | 健康檢查 | 每日 | - |

## 🔧 Synology DSM 部署步驟

### 1. 上傳腳本到 NAS
```bash
# 複製腳本到 NAS
scp schedule_reports.sh admin@192.168.0.222:/volume1/ai-stack2/redmine-report/
```

### 2. 設定執行權限
```bash
# SSH 登入 NAS
ssh admin@192.168.0.222

# 設定權限
chmod +x /volume1/ai-stack2/redmine-report/schedule_reports.sh

# 創建日誌目錄
mkdir -p /volume1/ai-stack2/redmine-report/logs
```

### 3. DSM 任務排程器設定

1. **開啟 DSM 控制台** → **任務排程器**
2. **建立新任務** → **排定的任務** → **使用者定義的指令碼**
3. **一般設定**：
   ```
   任務名稱: Redmine 報表自動發送
   使用者: root (或有權限的使用者)
   已啟用: ✓
   ```

4. **排程設定**：
   ```
   執行日期: 每天
   首次執行時間: 00:00
   頻率: 每 1 小時
   ```

5. **任務設定**：
   ```bash
   /volume1/ai-stack2/redmine-report/schedule_reports.sh
   ```

6. **設定** → **輸出** → 選擇將結果寄送至：
   ```
   admin@gogopeaks.com  # 接收執行結果通知
   ```

## ⚙️ 腳本配置參數

### 修改基本設定
編輯腳本開頭的設定區域：

```bash
# 修改 API 服務器地址
BASE_URL="http://192.168.0.222:3003"

# 修改日誌檔案位置
LOG_FILE="/volume1/ai-stack2/redmine-report/logs/schedule.log"
```

### 自訂排程時間
修改腳本中的時間判斷條件：

```bash
# 修改每日報表時間（目前是 08:00）
if [ "$HOUR" = "08" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then

# 修改週報時間（目前是週一 08:30）  
elif [ "$HOUR" = "08" ] && [ "$MINUTE" = "30" ] && [ "$DAY_OF_WEEK" = "1" ]; then
```

### 啟用額外排程
取消註解以啟用額外功能：

```bash
# 下午報表 (17:00)
if [ "$HOUR" = "17" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
    call_api 2 1  # 當日完工議題
fi

# 緊急專案報表 (12:00)
URGENT_PROJECT="金池三"
if [ "$HOUR" = "12" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
    call_api 1 3 "&project_filter=$URGENT_PROJECT"
fi
```

## 📊 日誌監控

### 查看即時日誌
```bash
# 查看最新日誌
tail -f /volume1/ai-stack2/redmine-report/logs/schedule.log

# 查看今日日誌
grep "$(date '+%Y-%m-%d')" /volume1/ai-stack2/redmine-report/logs/schedule.log

# 查看錯誤日誌
grep "❌" /volume1/ai-stack2/redmine-report/logs/schedule.log
```

### 日誌格式範例
```
[2024-12-09 08:00:01] 🚀 開始執行報表排程檢查 - 2024-12-09 08:00 (週1)
[2024-12-09 08:00:01] 📅 今天是工作日
[2024-12-09 08:00:01] ⏰ 開始發送每日報表 (08:00)
[2024-12-09 08:00:02] 📤 發送報表1 (14天資料) - URL: http://192.168.0.222:3003/send-email?report_type=1&auto_send=true&days=14
[2024-12-09 08:00:05] ✅ 報表1發送成功
[2024-12-09 08:00:35] 📤 發送報表2 (14天資料) - URL: http://192.168.0.222:3003/send-email?report_type=2&auto_send=true&days=14
[2024-12-09 08:00:38] ✅ 報表2發送成功
[2024-12-09 08:01:08] 📤 發送報表5 (14天資料) - URL: http://192.168.0.222:3003/send-email?report_type=5&auto_send=true&days=14
[2024-12-09 08:01:12] ✅ 報表5發送成功
[2024-12-09 08:01:42] ✅ 每日報表發送完成
[2024-12-09 08:01:42] 🏁 排程檢查結束
```

## 🧪 測試和驗證

### 手動執行測試
```bash
# 直接執行腳本測試
/volume1/ai-stack2/redmine-report/schedule_reports.sh

# 檢查執行結果
echo $?  # 0 表示成功
```

### API 連線測試
```bash
# 測試 API 服務可用性
curl -s "http://192.168.0.222:3003/health"

# 手動測試報表發送
curl -X POST "http://192.168.0.222:3003/send-email?report_type=1&auto_send=true&days=1"
```

### 模擬特定時間執行
修改腳本中的時間變數進行測試：

```bash
# 臨時修改測試
HOUR="08"
MINUTE="00" 
DAY_OF_WEEK="1"
```

## 🛠️ 故障排除

### 常見問題

1. **權限不足錯誤**
   ```bash
   # 確認腳本權限
   ls -la /volume1/ai-stack2/redmine-report/schedule_reports.sh
   # 應顯示 -rwxr-xr-x
   
   # 重新設定權限
   chmod +x /volume1/ai-stack2/redmine-report/schedule_reports.sh
   ```

2. **API 連線失敗**
   ```bash
   # 檢查服務狀態
   docker ps | grep redmine-report
   
   # 檢查服務日誌
   docker logs redmine-report-service
   
   # 測試網路連線
   curl -s "http://192.168.0.222:3003/health"
   ```

3. **日誌目錄不存在**
   ```bash
   # 創建日誌目錄
   mkdir -p /volume1/ai-stack2/redmine-report/logs
   chown -R admin:users /volume1/ai-stack2/redmine-report/logs
   ```

4. **任務排程器未執行**
   - 確認任務排程器中任務狀態為「已啟用」
   - 檢查使用者權限
   - 查看任務排程器的執行記錄

### 錯誤代碼含義

| 錯誤訊息 | 可能原因 | 解決方法 |
|----------|----------|----------|
| `Connection refused` | 服務未啟動 | 啟動 redmine-report 服務 |
| `HTTP 404` | API 端點錯誤 | 確認 API 路徑正確 |
| `HTTP 500` | 伺服器內部錯誤 | 檢查伺服器日誌 |
| `Timeout` | 網路連線問題 | 檢查網路設定 |

## 🎯 最佳實務建議

1. **監控設定**
   - 設定日誌輪替，避免日誌檔過大
   - 定期檢查排程執行狀況
   - 設定異常通知機制

2. **備份策略**
   - 定期備份腳本和設定
   - 記錄自訂修改內容
   - 建立緊急復原計畫

3. **效能優化**
   - 避免報表發送時間重疊
   - 在系統低負載時間執行大量報表
   - 定期清理舊日誌檔

4. **安全性考量**
   - 限制腳本執行權限
   - 定期更新相關密碼
   - 監控異常執行狀況

## 🚀 部署完成後檢查清單

- [ ] 腳本已上傳到正確位置
- [ ] 執行權限已設定（755）
- [ ] 日誌目錄已創建
- [ ] DSM 任務排程器已設定
- [ ] API 服務正常運作
- [ ] 手動執行測試通過
- [ ] 日誌記錄正常
- [ ] 錯誤通知機制已設定

完成上述設定後，您的 Redmine 報表系統將完全自動化運行！ 🎉
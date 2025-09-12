#!/bin/bash
# Redmine 報表自動排程腳本
# 版本: 1.0
# 用途: 自動化發送 Redmine 報表
# 使用方式: 在 Synology DSM 任務排程器中設定每小時執行一次

# ==============================================
# 基本設定
# ==============================================
BASE_URL="http://192.168.0.222:3003"
LOG_FILE="/volume1/ai-stack2/redmine-report/logs/schedule.log"

# 創建日誌目錄（如果不存在）
mkdir -p "$(dirname "$LOG_FILE")"

# 日誌函數
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 錯誤處理函數
handle_error() {
    local report_type=$1
    local error_msg=$2
    log "❌ 報表${report_type}發送失敗: $error_msg"
}

# 成功處理函數
handle_success() {
    local report_type=$1
    log "✅ 報表${report_type}發送成功"
}

# API 調用函數
call_api() {
    local report_type=$1
    local days=$2
    local extra_params=${3:-""}
    
    local url="$BASE_URL/send-email?report_type=$report_type&auto_send=true&days=$days$extra_params"
    
    log "📤 發送報表${report_type} (${days}天資料) - URL: $url"
    
    # 使用 curl 發送請求，設定超時時間
    local response
    response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        --max-time 60 \
        --connect-timeout 10 \
        -w "HTTPCODE:%{http_code}")
    
    local http_code
    http_code=$(echo "$response" | grep -o "HTTPCODE:[0-9]*" | cut -d: -f2)
    local body
    body=$(echo "$response" | sed 's/HTTPCODE:[0-9]*$//')
    
    # 檢查 HTTP 狀態碼
    if [ "$http_code" = "200" ]; then
        handle_success "$report_type"
        return 0
    else
        handle_error "$report_type" "HTTP $http_code - $body"
        return 1
    fi
}

# ==============================================
# 主要邏輯
# ==============================================

# 取得當前時間資訊
CURRENT_TIME=$(date '+%H:%M')
HOUR=$(date +%H)
MINUTE=$(date +%M)
DAY_OF_WEEK=$(date +%u)  # 1=週一, 7=週日
DATE_STR=$(date '+%Y-%m-%d')

log "🚀 開始執行報表排程檢查 - $DATE_STR $CURRENT_TIME (週$DAY_OF_WEEK)"

# 檢查是否為工作日 (週一到週五)
if [ "$DAY_OF_WEEK" -ge 1 ] && [ "$DAY_OF_WEEK" -le 5 ]; then
    IS_WORKDAY=true
    log "📅 今天是工作日"
else
    IS_WORKDAY=false
    log "📅 今天是週末"
fi

# ==============================================
# 每日 08:00 報表發送 (工作日)
# ==============================================
if [ "$HOUR" = "08" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
    log "⏰ 開始發送每日報表 (08:00)"
    
    # 報表一：議題狀態統計 (14天資料)
    call_api 1 14
    sleep 30
    
    # 報表二：完工議題清單 (14天資料)
    call_api 2 14
    sleep 30
    
    # 報表五：近期施工照片 (14天資料)
    call_api 5 14
    sleep 30
    
    log "✅ 每日報表發送完成"

# ==============================================
# 每週一 08:30 週報發送
# ==============================================
elif [ "$HOUR" = "08" ] && [ "$MINUTE" = "30" ] && [ "$DAY_OF_WEEK" = "1" ]; then
    log "⏰ 開始發送週報 (週一 08:30)"
    
    # 報表三：專案週報 (7天資料)
    call_api 3 7
    
    log "✅ 週報發送完成"

# ==============================================
# 每月第一個工作日 09:00 月報發送 (可選)
# ==============================================
elif [ "$HOUR" = "09" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
    # 檢查是否為當月第一個工作日
    DAY_OF_MONTH=$(date +%d)
    if [ "$DAY_OF_MONTH" -le 7 ]; then  # 前7天內
        FIRST_WORKDAY_OF_MONTH=$(date -d "$(date +%Y-%m-01)" '+%u')
        if [ "$FIRST_WORKDAY_OF_MONTH" -gt 5 ]; then
            # 如果1號是週末，找下一個工作日
            EXPECTED_DAY=$((8 - $FIRST_WORKDAY_OF_MONTH + 1))
        else
            EXPECTED_DAY=1
        fi
        
        if [ "$DAY_OF_MONTH" -eq "$EXPECTED_DAY" ]; then
            log "⏰ 開始發送月報 (當月第一個工作日 09:00)"
            
            # 報表三：專案月報 (30天資料)
            call_api 3 30
            
            log "✅ 月報發送完成"
        fi
    fi

# ==============================================
# 手動測試模式 (每日 23:59)
# ==============================================
elif [ "$HOUR" = "23" ] && [ "$MINUTE" = "59" ]; then
    log "🧪 執行每日健康檢查"
    
    # 測試 API 連線
    health_check=$(curl -s "$BASE_URL/health" --max-time 10 --connect-timeout 5)
    if [ $? -eq 0 ]; then
        log "💚 系統健康檢查通過: $health_check"
    else
        log "❤️ 系統健康檢查失敗"
    fi

else
    # 非排程時間，不執行任何操作
    log "⏸️ 非排程時間，跳過執行"
fi

# ==============================================
# 特殊排程範例 (可根據需要啟用)
# ==============================================

# 如果需要每日下午報表，取消下面註解
# if [ "$HOUR" = "17" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
#     log "⏰ 開始發送下午報表 (17:00)"
#     
#     # 當日完工議題 (1天資料)
#     call_api 2 1
#     
#     log "✅ 下午報表發送完成"
# fi

# 如果需要緊急專案報表，取消下面註解並修改條件
# URGENT_PROJECT="緊急專案名稱"
# if [ "$HOUR" = "12" ] && [ "$MINUTE" = "00" ] && [ "$IS_WORKDAY" = true ]; then
#     log "⏰ 開始發送緊急專案報表 (12:00)"
#     
#     # 緊急專案報表 (3天資料)
#     call_api 1 3 "&project_filter=$URGENT_PROJECT"
#     
#     log "✅ 緊急專案報表發送完成"
# fi

log "🏁 排程檢查結束\n"

# ==============================================
# 日誌清理 (保留最近30天)
# ==============================================
find "$(dirname "$LOG_FILE")" -name "*.log" -type f -mtime +30 -delete 2>/dev/null

exit 0
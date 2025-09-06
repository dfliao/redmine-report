# Synology 密碼變更功能設定指南

## 概述

現在系統已經整合真正的 Synology DSM 和 LDAP 密碼變更功能。本指南將協助您正確設定環境變數和測試功能。

## 🔧 環境設定

### 1. DSM API 設定

在您的 `.env` 檔案中設定以下變數：

```bash
# Synology DSM 設定
SYNOLOGY_DSM_HOST=192.168.0.222          # 您的 NAS IP 位址
SYNOLOGY_DSM_PORT=5001                    # DSM HTTPS 連接埠 (通常是 5001)
SYNOLOGY_DSM_ADMIN_USER=admin             # DSM 管理員帳號
SYNOLOGY_DSM_ADMIN_PASS=您的管理員密碼     # DSM 管理員密碼
```

### 2. LDAP 設定

```bash
# Synology LDAP 設定
LDAP_HOST=192.168.0.222                   # LDAP 伺服器 IP (通常與 DSM 相同)
LDAP_PORT=389                             # LDAP 連接埠 (通常是 389)
LDAP_ADMIN_DN=cn=root,dc=gogopeaks,dc=com # LDAP 管理員 DN
LDAP_ADMIN_PASS=您的LDAP管理員密碼         # LDAP 管理員密碼
LDAP_BASE_DN=cn=users,dc=gogopeaks,dc=com # 使用者基底 DN
```

## 🚀 功能特色

### ✅ **已實現功能**
- ✅ 真正的 Synology DSM 使用者密碼變更 (透過 Web API)
- ✅ 真正的 LDAP 使用者密碼變更 (透過 LDAP 協定)
- ✅ 連線測試功能 - 驗證 DSM 和 LDAP 連線狀態
- ✅ 完整錯誤處理和使用者反饋
- ✅ 管理員可變更他人密碼，一般使用者只能變更自己的密碼
- ✅ 密碼複雜度驗證 (至少 8 個字元)
- ✅ 系統選擇 - 可以只變更 DSM 或只變更 LDAP

### 🔧 **技術架構**
- **DSM 整合**: 使用 Synology Web API 2.0
- **LDAP 整合**: 使用 ldap3 Python 套件
- **安全性**: HTTPS 連線、會話管理、權限控制
- **錯誤處理**: 完整的錯誤代碼對應和使用者友善訊息

## 📝 使用步驟

### 1. 測試連線
1. 開啟 `/change-password` 頁面
2. 點擊「測試連線」按鈕
3. 查看 DSM 和 LDAP 連線狀態
4. 確認兩個系統都顯示「連線測試成功」

### 2. 變更密碼
1. 輸入您的 Redmine 管理員帳號密碼進行認證
2. 選擇要變更密碼的使用者 (管理員可選擇他人)
3. 設定新密碼 (至少 8 個字元)
4. 選擇要變更的系統 (DSM、LDAP 或兩者)
5. 點擊「變更密碼」執行

### 3. 查看結果
- ✅ **成功**: 顯示「密碼變更完成」訊息
- ❌ **失敗**: 顯示具體錯誤原因和解決建議
- 🔄 **部分成功**: 顯示成功和失敗的項目

## 🔍 故障排除

### 常見錯誤和解決方案

#### 1. DSM 連線失敗
**錯誤訊息**: `DSM連線錯誤: Connection refused`
**解決方案**:
- 確認 `SYNOLOGY_DSM_HOST` 和 `SYNOLOGY_DSM_PORT` 設定正確
- 確認 DSM 服務正在運作
- 檢查防火牆設定是否阻擋連線

#### 2. DSM 認證失敗  
**錯誤訊息**: `DSM管理員認證失敗: 帳號或密碼錯誤`
**解決方案**:
- 確認 `SYNOLOGY_DSM_ADMIN_USER` 和 `SYNOLOGY_DSM_ADMIN_PASS` 正確
- 確認管理員帳號已啟用且未被鎖定
- 檢查是否啟用雙因素認證 (需要暫時停用或使用應用程式密碼)

#### 3. LDAP 連線失敗
**錯誤訊息**: `LDAP連線錯誤: Can't contact LDAP server`
**解決方案**:
- 確認 `LDAP_HOST` 和 `LDAP_PORT` 設定正確
- 確認 LDAP Server 套件已安裝並啟用
- 檢查 LDAP 服務設定中的連接埠

#### 4. LDAP 使用者不存在
**錯誤訊息**: `LDAP使用者不存在: username`
**解決方案**:
- 確認使用者已在 LDAP 中建立
- 檢查 `LDAP_BASE_DN` 設定是否正確
- 確認使用者 DN 格式符合您的 LDAP 架構

### 📋 檢查清單

在使用密碼變更功能前，請確認：

- [ ] ✅ DSM Web API 已啟用
- [ ] ✅ LDAP Server 套件已安裝且啟用
- [ ] ✅ 環境變數已正確設定
- [ ] ✅ 管理員帳號密碼正確
- [ ] ✅ 網路連線正常
- [ ] ✅ 目標使用者在兩個系統中都存在
- [ ] ✅ 新密碼符合複雜度要求

## 🛡️ 安全性考量

### 1. 權限控制
- **管理員**: 可變更任何使用者密碼
- **一般使用者**: 只能變更自己的密碼
- **認證**: 需要通過 Redmine 認證才能存取功能

### 2. 密碼安全
- **長度**: 最少 8 個字元
- **建議**: 包含大小寫字母、數字和特殊符號
- **傳輸**: 使用 HTTPS 加密傳輸
- **儲存**: 不在日誌中記錄密碼內容

### 3. 連線安全
- **DSM**: 使用 HTTPS 連線，忽略自簽證書
- **LDAP**: 使用標準 LDAP 協定
- **會話**: DSM 會話在操作完成後自動登出

## 🔄 API 文檔

### 測試連線 API
```bash
GET /api/test-synology-connection
```

**回應範例**:
```json
{
  "success": true,
  "data": {
    "dsm": {
      "success": true,
      "message": "DSM API連線測試成功"
    },
    "ldap": {
      "success": true,
      "message": "LDAP連線測試成功"
    }
  }
}
```

### 密碼變更 API
```bash
POST /change-password-execute
Content-Type: application/x-www-form-urlencoded

target_user=username
new_password=newpass123
confirm_password=newpass123
change_dsm=true
change_ldap=true
```

## 📞 支援資訊

如果遇到問題無法解決，請檢查：

1. **系統日誌**: 
   ```bash
   docker logs redmine-report-service
   ```

2. **連線測試**: 在密碼變更頁面點擊「測試連線」

3. **環境變數**: 確認所有必要的環境變數都已正確設定

4. **權限**: 確認管理員帳號有足夠權限執行密碼變更操作

---

**✅ 現在您可以安全地變更 Synology DSM 和 LDAP 使用者密碼了！**
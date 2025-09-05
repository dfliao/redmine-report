# Synology 密碼變更功能需求文檔

## 概述

目前的密碼變更功能(`/change-password`)僅提供UI界面和成功消息顯示，但實際上並未執行真正的Synology DSM與LDAP密碼變更操作。本文檔記錄實現真實密碼變更功能所需的技術需求和系統整合方案。

## 當前狀況

### 已實現功能
- ✅ Web界面 (`/change-password`)
- ✅ 使用者認證 (管理員可修改他人密碼，一般使用者只能修改自己密碼)
- ✅ 表單驗證和UI反饋
- ✅ 成功消息顯示

### 缺失功能
- ❌ 實際Synology DSM密碼變更
- ❌ 實際LDAP密碼變更
- ❌ 密碼複雜度驗證
- ❌ 錯誤處理和回滾機制

## 技術需求

### 1. Synology DSM密碼變更

#### API方式 (建議)
```bash
# Synology DSM Web API 2.0
POST https://[DSM_HOST]/webapi/auth.cgi
# 需要admin權限token獲取使用者管理API存取權

POST https://[DSM_HOST]/webapi/entry.cgi
api: SYNO.Core.User.Password
method: set
user: [username]
new_password: [new_password]
```

#### SSH方式 (備選)
```bash
# 透過SSH執行系統命令
ssh admin@[DSM_HOST] "synouser --setpw [username] [new_password]"
```

### 2. LDAP密碼變更

#### LDAP Modify Operation
```python
import ldap3
from ldap3 import Server, Connection, MODIFY_REPLACE

# LDAP連接設定
server = Server('ldap://[LDAP_HOST]:389')
conn = Connection(server, user='cn=admin,dc=example,dc=com', password='admin_pwd')

# 密碼變更操作
conn.modify(
    'cn=[username],ou=users,dc=example,dc=com',
    {'userPassword': [(MODIFY_REPLACE, [new_password])]}
)
```

### 3. 環境變數配置需求

```bash
# Synology DSM設定
SYNOLOGY_DSM_HOST=your_nas_ip
SYNOLOGY_DSM_ADMIN_USERNAME=admin
SYNOLOGY_DSM_ADMIN_PASSWORD=admin_password

# LDAP設定
LDAP_HOST=your_ldap_host
LDAP_PORT=389
LDAP_ADMIN_DN=cn=admin,dc=example,dc=com
LDAP_ADMIN_PASSWORD=ldap_admin_password
LDAP_BASE_DN=ou=users,dc=example,dc=com
```

## 實作建議

### Phase 1: DSM整合
1. 安裝必要依賴：`requests`
2. 建立`SynologyService`類別
3. 實作DSM Web API認證和密碼變更
4. 測試DSM密碼變更功能

### Phase 2: LDAP整合  
1. 安裝必要依賴：`ldap3`
2. 建立`LDAPService`類別
3. 實作LDAP連接和密碼變更
4. 測試LDAP密碼變更功能

### Phase 3: 整合與錯誤處理
1. 修改現有`change_password`端點
2. 加入交易性操作 (如DSM成功但LDAP失敗需回滾)
3. 實作完整錯誤處理和使用者反饋
4. 加入審計日誌記錄

## 代碼架構建議

```python
# src/main/python/services/synology_service.py
class SynologyService:
    async def change_user_password(self, username: str, new_password: str) -> bool:
        """Change password in Synology DSM"""
        pass

# src/main/python/services/ldap_service.py  
class LDAPService:
    async def change_user_password(self, username: str, new_password: str) -> bool:
        """Change password in LDAP directory"""
        pass

# 在web/app.py中的整合
@app.post("/api/change-password")
async def change_password_api(request: PasswordChangeRequest):
    try:
        # 1. 驗證當前密碼
        # 2. 變更DSM密碼
        dsm_success = await synology_service.change_user_password(username, new_password)
        if not dsm_success:
            raise Exception("DSM密碼變更失敗")
        
        # 3. 變更LDAP密碼
        ldap_success = await ldap_service.change_user_password(username, new_password) 
        if not ldap_success:
            # 回滾DSM密碼變更
            await synology_service.change_user_password(username, old_password)
            raise Exception("LDAP密碼變更失敗")
            
        return {"success": True, "message": "密碼變更成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
```

## 安全性考量

### 1. 密碼複雜度要求
- 最小長度：8個字元
- 必須包含：大小寫字母、數字、特殊符號
- 不可與前3次使用過的密碼相同

### 2. 權限控制
- 管理員：可變更任何使用者密碼
- 一般使用者：僅可變更自己密碼
- 需驗證當前密碼 (一般使用者)

### 3. 審計日誌
- 記錄所有密碼變更操作
- 包含：時間戳記、操作者、目標使用者、結果狀態
- 存儲於安全日誌檔案

## 測試策略

### 單元測試
- DSM API連接測試
- LDAP連接測試  
- 密碼複雜度驗證測試
- 權限控制測試

### 整合測試
- 完整密碼變更流程測試
- 錯誤情境測試 (網路中斷、認證失敗等)
- 回滾機制測試

### 使用者接受測試
- 管理員變更他人密碼測試
- 一般使用者變更自己密碼測試
- UI/UX流程測試

## 部署注意事項

1. **環境變數設定**: 確保所有LDAP和DSM連接參數正確配置
2. **網路連通性**: 確保容器可存取DSM和LDAP服務
3. **權限設定**: 確保管理員帳號具有必要的DSM和LDAP管理權限
4. **備份策略**: 實作前先備份現有使用者資料
5. **監控設定**: 設定密碼變更操作的監控和告警

## 預期時程

- **Phase 1 (DSM整合)**: 2-3天
- **Phase 2 (LDAP整合)**: 2-3天  
- **Phase 3 (整合測試)**: 1-2天
- **總計**: 約1週完成

---

**注意**: 此功能涉及系統安全性，建議在測試環境完整驗證後再部署至生產環境。
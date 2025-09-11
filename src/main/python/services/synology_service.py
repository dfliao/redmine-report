#!/usr/bin/env python3
"""
Synology Service

Service for managing Synology DSM users and LDAP integration.
"""

import logging
import requests
import ldap3
from typing import Dict, Optional, List
from ldap3 import Server, Connection, MODIFY_REPLACE, ALL
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class SynologyService:
    """Service for Synology DSM and LDAP user management"""
    
    def __init__(self, settings):
        self.settings = settings
        
        # Synology DSM settings - use direct settings attributes
        self.dsm_host = settings.SYNOLOGY_DSM_HOST
        self.dsm_port = settings.SYNOLOGY_DSM_PORT
        self.dsm_admin_user = settings.SYNOLOGY_DSM_ADMIN_USER
        self.dsm_admin_pass = settings.SYNOLOGY_DSM_ADMIN_PASS
        
        # LDAP settings - use direct settings attributes
        self.ldap_host = settings.LDAP_HOST
        self.ldap_port = settings.LDAP_PORT
        self.ldap_admin_dn = settings.LDAP_ADMIN_DN
        self.ldap_admin_pass = settings.LDAP_ADMIN_PASS
        self.ldap_base_dn = settings.LDAP_BASE_DN
        self.ldap_login_attr = settings.LDAP_LOGIN_ATTR
        
        # Debug logging to check if password is loaded
        logger.info(f"LDAP Admin DN: {self.ldap_admin_dn}")
        logger.info(f"LDAP Admin Pass loaded: {bool(self.ldap_admin_pass)}")
        logger.info(f"LDAP Admin Pass length: {len(self.ldap_admin_pass) if self.ldap_admin_pass else 0}")
        
        # Session management
        self.dsm_session = None
        self.dsm_sid = None
        
        logger.info("Initialized Synology service")
    
    async def change_dsm_user_password(self, username: str, new_password: str) -> Dict[str, any]:
        """Change password for a DSM user using Synology Web API"""
        try:
            logger.info(f"Attempting to change DSM password for user: {username}")
            
            # Step 1: Authenticate as admin
            auth_result = await self._authenticate_dsm_admin()
            if not auth_result['success']:
                return auth_result
            
            # Step 2: Change user password
            api_url = f"https://{self.dsm_host}:{self.dsm_port}/webapi/entry.cgi"
            
            params = {
                'api': 'SYNO.Core.User.PasswordPolicy',
                'version': '1',
                'method': 'set',
                '_sid': self.dsm_sid,
                'username': username,
                'password': new_password
            }
            
            response = requests.post(api_url, data=params, verify=False, timeout=10)
            result = response.json()
            
            if result.get('success', False):
                logger.info(f"DSM password changed successfully for user: {username}")
                return {
                    'success': True,
                    'message': f'DSM密碼變更成功 - 使用者: {username}'
                }
            else:
                error_code = result.get('error', {}).get('code', 'unknown')
                error_msg = self._get_dsm_error_message(error_code)
                logger.error(f"DSM password change failed for {username}: {error_msg} (code: {error_code})")
                return {
                    'success': False,
                    'message': f'DSM密碼變更失敗: {error_msg}'
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"DSM API request error for {username}: {e}")
            return {
                'success': False,
                'message': f'DSM連線錯誤: {str(e)}'
            }
        except Exception as e:
            logger.error(f"DSM password change error for {username}: {e}")
            return {
                'success': False,
                'message': f'DSM密碼變更發生錯誤: {str(e)}'
            }
        finally:
            # Logout from DSM
            await self._logout_dsm()
    
    async def change_ldap_user_password(self, username: str, new_password: str) -> Dict[str, any]:
        """Change password for an LDAP user"""
        try:
            logger.info(f"Attempting to change LDAP password for user: {username}")
            
            # Connect to LDAP server
            server = Server(f'ldap://{self.ldap_host}:{self.ldap_port}', get_info=ALL)
            conn = Connection(server, user=self.ldap_admin_dn, password=self.ldap_admin_pass, auto_bind=True)
            
            # Construct user DN using the login attribute (uid)
            user_dn = f'{self.ldap_login_attr}={username},{self.ldap_base_dn}'
            
            # Search for the user to verify existence
            search_base = self.ldap_base_dn
            search_filter = f'({self.ldap_login_attr}={username})'
            search_result = conn.search(search_base, search_filter)
            
            if not search_result or not conn.entries:
                logger.error(f"LDAP user not found: {username}")
                conn.unbind()
                return {
                    'success': False,
                    'message': f'LDAP使用者不存在: {username} (搜尋條件: {search_filter})'
                }
            
            # Use the actual DN from search results
            actual_user_dn = str(conn.entries[0].entry_dn)
            logger.info(f"Found LDAP user DN: {actual_user_dn}")
            
            # Change password using the correct DN
            modify_result = conn.modify(actual_user_dn, {'userPassword': [(MODIFY_REPLACE, [new_password])]})
            
            if modify_result:
                logger.info(f"LDAP password changed successfully for user: {username}")
                conn.unbind()
                return {
                    'success': True,
                    'message': f'LDAP密碼變更成功 - 使用者: {username}'
                }
            else:
                error_msg = conn.last_error or 'Unknown error'
                logger.error(f"LDAP password change failed for {username}: {error_msg}")
                conn.unbind()
                return {
                    'success': False,
                    'message': f'LDAP密碼變更失敗: {error_msg}'
                }
                
        except ldap3.core.exceptions.LDAPException as e:
            logger.error(f"LDAP connection error for {username}: {e}")
            return {
                'success': False,
                'message': f'LDAP連線錯誤: {str(e)}'
            }
        except Exception as e:
            logger.error(f"LDAP password change error for {username}: {e}")
            return {
                'success': False,
                'message': f'LDAP密碼變更發生錯誤: {str(e)}'
            }
    
    async def _authenticate_dsm_admin(self) -> Dict[str, any]:
        """Authenticate with DSM as admin to get session"""
        try:
            auth_url = f"https://{self.dsm_host}:{self.dsm_port}/webapi/auth.cgi"
            
            params = {
                'api': 'SYNO.API.Auth',
                'version': '6',
                'method': 'login',
                'account': self.dsm_admin_user,
                'passwd': self.dsm_admin_pass,
                'session': 'UserSettings',
                'format': 'sid',
                'enable_syno_token': 'yes',
                'enable_device_token': 'yes'
            }
            
            response = requests.post(auth_url, data=params, verify=False, timeout=10)
            result = response.json()
            
            if result.get('success', False):
                self.dsm_sid = result['data']['sid']
                logger.info("DSM admin authentication successful")
                return {
                    'success': True,
                    'message': 'DSM認證成功'
                }
            else:
                error_code = result.get('error', {}).get('code', 'unknown')
                error_msg = self._get_dsm_error_message(error_code)
                
                # Special handling for 2FA errors
                if error_code == 403 or error_code == 404:
                    logger.warning(f"DSM admin authentication failed due to 2FA: {error_msg}")
                    return {
                        'success': False,
                        'message': f'DSM管理員認證失敗: {error_msg} (建議關閉2FA或使用專用API用戶)'
                    }
                else:
                    logger.error(f"DSM admin authentication failed: {error_msg}")
                    return {
                        'success': False,
                        'message': f'DSM管理員認證失敗: {error_msg}'
                    }
                
        except Exception as e:
            logger.error(f"DSM admin authentication error: {e}")
            return {
                'success': False,
                'message': f'DSM認證發生錯誤: {str(e)}'
            }
    
    async def _logout_dsm(self):
        """Logout from DSM session"""
        try:
            if self.dsm_sid:
                logout_url = f"https://{self.dsm_host}:{self.dsm_port}/webapi/auth.cgi"
                
                params = {
                    'api': 'SYNO.API.Auth',
                    'version': '1',
                    'method': 'logout',
                    'session': 'UserSettings',
                    '_sid': self.dsm_sid
                }
                
                requests.post(logout_url, data=params, verify=False, timeout=5)
                logger.info("DSM session logged out")
                
        except Exception as e:
            logger.warning(f"DSM logout error (non-critical): {e}")
        finally:
            self.dsm_sid = None
    
    def _get_dsm_error_message(self, error_code: int) -> str:
        """Get human readable error message for DSM error codes"""
        error_messages = {
            100: '未知錯誤',
            101: '參數無效',
            102: 'API不存在',
            103: '方法不存在',
            104: '不支援的版本',
            105: '權限不足',
            106: '會話超時，請重新登入',
            107: '會話中斷',
            400: '執行失敗',
            401: '帳號或密碼錯誤',
            402: '沒有權限執行此操作',
            403: '一次性密碼錯誤',
            404: '兩階段驗證失敗',
            407: '密碼過期需要變更',
            408: '密碼必須變更',
            409: '帳號已被停用',
            410: '帳號已過期',
            411: '密碼已過期',
            412: '密碼變更失敗',
            413: '帳號已被鎖定'
        }
        
        return error_messages.get(error_code, f'未知錯誤 (代碼: {error_code})')
    
    async def test_dsm_connection(self) -> Dict[str, any]:
        """Test DSM API connection"""
        try:
            test_url = f"https://{self.dsm_host}:{self.dsm_port}/webapi/query.cgi"
            params = {
                'api': 'SYNO.API.Info',
                'version': '1',
                'method': 'query',
                'query': 'SYNO.API.Auth'
            }
            
            response = requests.get(test_url, params=params, verify=False, timeout=10)
            result = response.json()
            
            if result.get('success', False):
                return {
                    'success': True,
                    'message': 'DSM API連線測試成功'
                }
            else:
                return {
                    'success': False,
                    'message': 'DSM API連線測試失敗'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'DSM連線測試錯誤: {str(e)}'
            }
    
    async def test_ldap_connection(self) -> Dict[str, any]:
        """Test LDAP connection"""
        try:
            # Check if admin password is provided
            if not self.ldap_admin_pass:
                return {
                    'success': False,
                    'message': 'LDAP管理員密碼未設定 (LDAP_ADMIN_PASS)'
                }
            
            server = Server(f'ldap://{self.ldap_host}:{self.ldap_port}')
            conn = Connection(
                server, 
                user=self.ldap_admin_dn, 
                password=self.ldap_admin_pass,
                auto_bind=False
            )
            
            # Try to bind
            bind_result = conn.bind()
            
            if bind_result:
                # Test a basic search to verify access
                search_result = conn.search(self.ldap_base_dn, '(objectClass=*)', search_scope='LEVEL')
                conn.unbind()
                
                if search_result:
                    return {
                        'success': True,
                        'message': f'LDAP連線測試成功 (DN: {self.ldap_admin_dn})'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'LDAP認證成功但無法搜尋基底DN: {self.ldap_base_dn}'
                    }
            else:
                error_msg = conn.last_error or '認證失敗'
                return {
                    'success': False,
                    'message': f'LDAP連線測試失敗：{error_msg}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'LDAP連線測試錯誤: {str(e)}'
            }
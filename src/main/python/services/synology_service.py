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
        
        # Synology DSM settings
        self.dsm_host = getattr(settings, 'SYNOLOGY_DSM_HOST', 'localhost')
        self.dsm_port = getattr(settings, 'SYNOLOGY_DSM_PORT', 5001)
        self.dsm_admin_user = getattr(settings, 'SYNOLOGY_DSM_ADMIN_USER', 'admin')
        self.dsm_admin_pass = getattr(settings, 'SYNOLOGY_DSM_ADMIN_PASS', '')
        
        # LDAP settings
        self.ldap_host = getattr(settings, 'LDAP_HOST', 'localhost')
        self.ldap_port = getattr(settings, 'LDAP_PORT', 389)
        self.ldap_admin_dn = getattr(settings, 'LDAP_ADMIN_DN', 'cn=root,dc=example,dc=com')
        self.ldap_admin_pass = getattr(settings, 'LDAP_ADMIN_PASS', '')
        self.ldap_base_dn = getattr(settings, 'LDAP_BASE_DN', 'cn=users,dc=example,dc=com')
        
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
            
            # Search for the user
            user_dn = f'cn={username},{self.ldap_base_dn}'
            search_result = conn.search(user_dn, '(objectClass=*)')
            
            if not search_result:
                logger.error(f"LDAP user not found: {username}")
                return {
                    'success': False,
                    'message': f'LDAP使用者不存在: {username}'
                }
            
            # Change password
            modify_result = conn.modify(user_dn, {'userPassword': [(MODIFY_REPLACE, [new_password])]})
            
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
                'format': 'sid'
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
            server = Server(f'ldap://{self.ldap_host}:{self.ldap_port}')
            conn = Connection(server, user=self.ldap_admin_dn, password=self.ldap_admin_pass)
            
            if conn.bind():
                conn.unbind()
                return {
                    'success': True,
                    'message': 'LDAP連線測試成功'
                }
            else:
                return {
                    'success': False,
                    'message': 'LDAP連線測試失敗：認證錯誤'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'LDAP連線測試錯誤: {str(e)}'
            }
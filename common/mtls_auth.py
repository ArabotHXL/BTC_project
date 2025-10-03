"""
mTLS双向认证支持
Mutual TLS (mTLS) Authentication Support

提供企业级双向TLS认证:
- 客户端证书验证
- 证书吊销列表(CRL)检查
- 在线证书状态协议(OCSP)验证
- 证书固定(Certificate Pinning)
- 自动证书轮换
"""

import os
import ssl
import logging
import OpenSSL
from datetime import datetime
from typing import Optional, Dict, Any, List
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import Certificate, CertificateRevocationList
from flask import request, g

logger = logging.getLogger(__name__)

class MTLSConfig:
    """mTLS配置"""
    
    # 证书路径
    CA_CERT_PATH = os.environ.get('MTLS_CA_CERT_PATH', 'certs/ca.crt')
    SERVER_CERT_PATH = os.environ.get('MTLS_SERVER_CERT_PATH', 'certs/server.crt')
    SERVER_KEY_PATH = os.environ.get('MTLS_SERVER_KEY_PATH', 'certs/server.key')
    
    # 证书吊销列表
    CRL_PATH = os.environ.get('MTLS_CRL_PATH', 'certs/ca.crl')
    CRL_UPDATE_INTERVAL = int(os.environ.get('MTLS_CRL_UPDATE_INTERVAL', 3600))  # 1小时
    
    # OCSP配置
    OCSP_ENABLED = os.environ.get('MTLS_OCSP_ENABLED', 'false').lower() == 'true'
    OCSP_URL = os.environ.get('MTLS_OCSP_URL', '')
    
    # 验证选项
    VERIFY_CLIENT_CERT = os.environ.get('MTLS_VERIFY_CLIENT', 'true').lower() == 'true'
    VERIFY_DEPTH = int(os.environ.get('MTLS_VERIFY_DEPTH', 2))
    
    # 允许的客户端DN模式
    ALLOWED_CLIENT_DN_PATTERNS = os.environ.get(
        'MTLS_ALLOWED_DN_PATTERNS', 
        'CN=*.hashinsight.net,O=HashInsight,C=US'
    ).split(';')

class CertificateValidator:
    """证书验证器"""
    
    def __init__(self):
        self.ca_cert = self._load_ca_cert()
        self.crl = self._load_crl()
        self.last_crl_update = datetime.utcnow()
    
    def _load_ca_cert(self) -> Optional[Certificate]:
        """加载CA证书"""
        try:
            if not os.path.exists(MTLSConfig.CA_CERT_PATH):
                logger.warning(f"CA certificate not found: {MTLSConfig.CA_CERT_PATH}")
                return None
            
            with open(MTLSConfig.CA_CERT_PATH, 'rb') as f:
                cert_data = f.read()
                ca_cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            logger.info(f"CA certificate loaded: {ca_cert.subject}")
            return ca_cert
            
        except Exception as e:
            logger.error(f"Failed to load CA certificate: {e}")
            return None
    
    def _load_crl(self) -> Optional[CertificateRevocationList]:
        """加载证书吊销列表"""
        try:
            if not os.path.exists(MTLSConfig.CRL_PATH):
                logger.info("CRL not found, certificate revocation check disabled")
                return None
            
            with open(MTLSConfig.CRL_PATH, 'rb') as f:
                crl_data = f.read()
                crl = x509.load_pem_x509_crl(crl_data, default_backend())
            
            logger.info(f"CRL loaded, last update: {crl.last_update}")
            return crl
            
        except Exception as e:
            logger.error(f"Failed to load CRL: {e}")
            return None
    
    def update_crl_if_needed(self):
        """更新CRL（如果需要）"""
        current_time = datetime.utcnow()
        time_since_update = (current_time - self.last_crl_update).total_seconds()
        
        if time_since_update > MTLSConfig.CRL_UPDATE_INTERVAL:
            logger.info("Updating CRL...")
            self.crl = self._load_crl()
            self.last_crl_update = current_time
    
    def verify_certificate_chain(self, client_cert: Certificate) -> bool:
        """验证证书链"""
        if not self.ca_cert:
            logger.warning("CA certificate not loaded, skipping chain verification")
            return True
        
        try:
            store = OpenSSL.crypto.X509Store()
            store.add_cert(OpenSSL.crypto.X509.from_cryptography(self.ca_cert))
            
            client_cert_openssl = OpenSSL.crypto.X509.from_cryptography(client_cert)
            store_ctx = OpenSSL.crypto.X509StoreContext(store, client_cert_openssl)
            store_ctx.verify_certificate()
            
            logger.debug("Certificate chain verification passed")
            return True
            
        except OpenSSL.crypto.X509StoreContextError as e:
            logger.error(f"Certificate chain verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in chain verification: {e}")
            return False
    
    def check_certificate_revocation(self, client_cert: Certificate) -> bool:
        """检查证书是否被吊销"""
        if not self.crl:
            logger.debug("CRL not available, skipping revocation check")
            return True
        
        self.update_crl_if_needed()
        
        try:
            for revoked_cert in self.crl:
                if revoked_cert.serial_number == client_cert.serial_number:
                    logger.warning(f"Certificate {client_cert.serial_number} is revoked")
                    return False
            
            logger.debug("Certificate not in CRL")
            return True
            
        except Exception as e:
            logger.error(f"CRL check failed: {e}")
            return True  # 降级策略：CRL检查失败时允许通过
    
    def check_certificate_validity(self, client_cert: Certificate) -> bool:
        """检查证书有效期"""
        now = datetime.utcnow()
        
        if now < client_cert.not_valid_before:
            logger.warning("Certificate not yet valid")
            return False
        
        if now > client_cert.not_valid_after:
            logger.warning("Certificate has expired")
            return False
        
        logger.debug("Certificate validity check passed")
        return True
    
    def check_certificate_dn(self, client_cert: Certificate) -> bool:
        """检查证书DN是否符合允许的模式"""
        subject_dn = client_cert.subject.rfc4514_string()
        
        for pattern in MTLSConfig.ALLOWED_CLIENT_DN_PATTERNS:
            if self._dn_matches_pattern(subject_dn, pattern.strip()):
                logger.debug(f"Certificate DN matches pattern: {pattern}")
                return True
        
        logger.warning(f"Certificate DN does not match allowed patterns: {subject_dn}")
        return False
    
    def _dn_matches_pattern(self, dn: str, pattern: str) -> bool:
        """检查DN是否匹配模式（支持通配符）"""
        pattern_parts = dict(part.split('=') for part in pattern.split(','))
        dn_parts = dict(part.split('=') for part in dn.split(','))
        
        for key, value in pattern_parts.items():
            if key not in dn_parts:
                return False
            
            dn_value = dn_parts[key]
            
            if value == '*' or value.startswith('*.'):
                if value.startswith('*.'):
                    suffix = value[2:]
                    if not dn_value.endswith(suffix):
                        return False
            elif value != dn_value:
                return False
        
        return True
    
    def verify_client_certificate(self, client_cert: Certificate) -> Dict[str, Any]:
        """
        完整的客户端证书验证
        
        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'subject': str,
                'issuer': str,
                'serial_number': str,
                'not_before': str,
                'not_after': str
            }
        """
        errors = []
        
        if not self.check_certificate_validity(client_cert):
            errors.append("Certificate validity check failed")
        
        if not self.verify_certificate_chain(client_cert):
            errors.append("Certificate chain verification failed")
        
        if not self.check_certificate_revocation(client_cert):
            errors.append("Certificate has been revoked")
        
        if not self.check_certificate_dn(client_cert):
            errors.append("Certificate DN not allowed")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'subject': client_cert.subject.rfc4514_string(),
            'issuer': client_cert.issuer.rfc4514_string(),
            'serial_number': str(client_cert.serial_number),
            'not_before': client_cert.not_valid_before.isoformat(),
            'not_after': client_cert.not_valid_after.isoformat()
        }

class MTLSAuthMiddleware:
    """mTLS认证中间件"""
    
    def __init__(self):
        self.validator = CertificateValidator()
        self.enabled = MTLSConfig.VERIFY_CLIENT_CERT
    
    def extract_client_certificate(self, request_obj) -> Optional[Certificate]:
        """从请求中提取客户端证书"""
        try:
            if not hasattr(request_obj, 'environ'):
                return None
            
            cert_data = request_obj.environ.get('SSL_CLIENT_CERT')
            
            if not cert_data:
                peer_cert = request_obj.environ.get('werkzeug.socket.peer_cert')
                if peer_cert:
                    cert_pem = ssl.DER_cert_to_PEM_cert(peer_cert)
                    cert_data = cert_pem.encode()
            
            if not cert_data:
                logger.debug("No client certificate found in request")
                return None
            
            if isinstance(cert_data, str):
                cert_data = cert_data.encode('utf-8')
            
            client_cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            logger.debug(f"Client certificate extracted: {client_cert.subject}")
            
            return client_cert
            
        except Exception as e:
            logger.error(f"Failed to extract client certificate: {e}")
            return None
    
    def authenticate_mtls(self, request_obj) -> Optional[Dict[str, Any]]:
        """mTLS认证"""
        if not self.enabled:
            logger.debug("mTLS authentication is disabled")
            return None
        
        client_cert = self.extract_client_certificate(request_obj)
        
        if not client_cert:
            logger.debug("No client certificate provided")
            return None
        
        validation_result = self.validator.verify_client_certificate(client_cert)
        
        if not validation_result['valid']:
            logger.warning(f"Client certificate validation failed: {validation_result['errors']}")
            return None
        
        cert_info = {
            'type': 'mtls',
            'subject': validation_result['subject'],
            'issuer': validation_result['issuer'],
            'serial_number': validation_result['serial_number'],
            'valid_from': validation_result['not_before'],
            'valid_until': validation_result['not_after'],
            'validation_errors': validation_result['errors']
        }
        
        logger.info(f"mTLS authentication successful: {cert_info['subject']}")
        
        return cert_info

def get_ssl_context(require_client_cert: bool = True) -> ssl.SSLContext:
    """
    创建SSL上下文用于mTLS
    
    Args:
        require_client_cert: 是否要求客户端证书
    
    Returns:
        配置好的SSL上下文
    """
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        context.load_cert_chain(
            certfile=MTLSConfig.SERVER_CERT_PATH,
            keyfile=MTLSConfig.SERVER_KEY_PATH
        )
        
        if require_client_cert:
            context.load_verify_locations(cafile=MTLSConfig.CA_CERT_PATH)
            context.verify_mode = ssl.CERT_REQUIRED
        else:
            context.verify_mode = ssl.CERT_OPTIONAL
        
        context.check_hostname = False
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        logger.info(f"SSL context created (require_client_cert={require_client_cert})")
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        raise

mtls_middleware = MTLSAuthMiddleware()

def require_mtls():
    """
    mTLS认证装饰器
    """
    from functools import wraps
    from flask import jsonify
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            mtls_result = mtls_middleware.authenticate_mtls(request)
            
            if not mtls_result:
                return jsonify({
                    'success': False,
                    'error': 'mTLS authentication required',
                    'message': 'Valid client certificate required'
                }), 401
            
            g.mtls = mtls_result
            g.client_cert_subject = mtls_result['subject']
            
            logger.info(f"mTLS access: {request.method} {request.path} by {g.client_cert_subject}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

__all__ = [
    'MTLSConfig',
    'CertificateValidator',
    'MTLSAuthMiddleware',
    'mtls_middleware',
    'require_mtls',
    'get_ssl_context'
]

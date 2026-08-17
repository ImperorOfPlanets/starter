"""
Модуль SSL сертификатов (ОС-зависимый)
"""

import os
from pathlib import Path
from OpenSSL import crypto

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('ssl')


class SslModule(BaseModule):
    """Модуль управления SSL сертификатами"""
    
    @staticmethod
    def check() -> bool:
        try:
            import OpenSSL
            return True
        except ImportError:
            return False
    
    @staticmethod
    def set_globals():
        """Устанавливает пути для SSL"""
        starter_path = get_global('starter_path')
        if starter_path:
            ssl_dir = starter_path / "files" / "web" / "ssl"
            set_global('ssl_dir', ssl_dir)
            logger.info(f"SSL directory: {ssl_dir}")
    
    @staticmethod
    def setup_ssl_folder() -> Path:
        """Создает папку для SSL если ее нет"""
        ssl_dir = get_global('ssl_dir')
        if ssl_dir is None:
            starter_path = get_global('starter_path')
            ssl_dir = starter_path / "files" / "web" / "ssl"
        
        ssl_dir.mkdir(parents=True, exist_ok=True)
        ssl_dir.chmod(0o755)
        return ssl_dir
    
    @staticmethod
    def check_existing_certificates() -> bool:
        """Проверяет наличие существующих сертификатов"""
        # ✅ ИСПРАВЛЕНО: SSLModule -> SslModule
        ssl_dir = SslModule.setup_ssl_folder()
        cert_file = ssl_dir / "selfsigned.crt"
        key_file = ssl_dir / "selfsigned.key"
        
        if cert_file.exists() and key_file.exists():
            try:
                with open(cert_file, "rb") as f:
                    crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
                with open(key_file, "rb") as f:
                    crypto.load_privatekey(crypto.FILETYPE_PEM, f.read())
                return True
            except:
                return False
        return False
    
    @staticmethod
    def generate_self_signed_cert(force_regenerate=False):
        """Генерирует самоподписанный SSL сертификат"""
        # ✅ ИСПРАВЛЕНО: используем SslModule (можно и self, но staticmethod требует класс)
        ssl_dir = SslModule.setup_ssl_folder()
        cert_file = ssl_dir / "selfsigned.crt"
        key_file = ssl_dir / "selfsigned.key"
        
        # ✅ ИСПРАВЛЕНО: SSLModule -> SslModule
        if not force_regenerate and SslModule.check_existing_certificates():
            return cert_file, key_file
        
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        
        cert = crypto.X509()
        subject = cert.get_subject()
        subject.C = "RU"
        subject.ST = "Moscow"
        subject.L = "Moscow"
        subject.O = "MyIDon"
        subject.CN = "localhost"
        
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)
        cert.set_issuer(subject)
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')
        
        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(key_file, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        
        return cert_file, key_file
    
    @staticmethod
    def get_ssl_context():
        """Возвращает SSL контекст"""
        try:
            # ✅ ИСПРАВЛЕНО: SSLModule -> SslModule
            cert_file, key_file = SslModule.generate_self_signed_cert()
            return (str(cert_file), str(key_file))
        except Exception as e:
            logger.error(f"Error getting SSL context: {e}")
            raise
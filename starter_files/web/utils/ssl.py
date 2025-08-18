import os
import sys

from OpenSSL import crypto
from pathlib import Path
from socket import gethostname

def setup_ssl_folder():
    """Создает папку для SSL если ее нет"""
    try:
        # Получаем абсолютный путь к директории скрипта
        script_dir = Path(sys.argv[0]).absolute().parent
        ssl_dir = script_dir / "starter_files" / "web" / "ssl"
        
        # Создаем папку (если не существует)
        ssl_dir.mkdir(parents=True, exist_ok=True)
        
        # Устанавливаем правильные права
        ssl_dir.chmod(0o755)
        return ssl_dir
    except Exception as e:
        logger.info(f"Ошибка создания SSL папки: {e}")
        raise

def check_existing_certificates():
    """Проверяет наличие существующих сертификатов"""
    ssl_dir = setup_ssl_folder()
    cert_file = ssl_dir / "selfsigned.crt"
    key_file = ssl_dir / "selfsigned.key"
    
    if cert_file.exists() and key_file.exists():
        try:
            # Проверяем валидность существующих сертификатов
            with open(cert_file, "rb") as f:
                crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
            with open(key_file, "rb") as f:
                crypto.load_privatekey(crypto.FILETYPE_PEM, f.read())
            return True
        except:
            # Если сертификаты повреждены, будем генерировать новые
            return False
    return False

def generate_self_signed_cert(force_regenerate=False):
    """Генерирует самоподписанный SSL сертификат, если его нет или force_regenerate=True"""
    ssl_dir = setup_ssl_folder()
    cert_file = ssl_dir / "selfsigned.crt"
    key_file = ssl_dir / "selfsigned.key"

    if not force_regenerate and check_existing_certificates():
        return cert_file, key_file

    # Генерация нового ключа
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # Создание сертификата
    cert = crypto.X509()
    subject = cert.get_subject()
    
    subject.C = "RU"
    subject.ST = "Moscow"
    subject.L = "Moscow"
    subject.O = "MyIDon"
    subject.CN = "localhost"
    
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 лет
    cert.set_issuer(subject)
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    # Сохранение файлов
    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

    return cert_file, key_file

def get_ssl_context():
    """Возвращает SSL контекст, используя существующие сертификаты или генерируя новые"""
    try:
        cert_file, key_file = generate_self_signed_cert()
        return (str(cert_file), str(key_file))
    except Exception as e:
        logger.info(f"Ошибка работы с SSL сертификатами: {e}")
        raise
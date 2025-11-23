import os
import sys
from datetime import datetime, timedelta

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from pathlib import Path
from socket import gethostname

from starter_files.core.utils.log_utils import LogManager

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
        logger = LogManager.get_logger('ssl')
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
                x509.load_pem_x509_certificate(f.read(), default_backend())
            with open(key_file, "rb") as f:
                serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
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
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Создание сертификата
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Moscow"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Moscow"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MyIDon"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365*10)  # 10 лет
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())

    # Сохранение файлов
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    return cert_file, key_file

def get_ssl_context():
    """Возвращает SSL контекст, используя существующие сертификаты или генерируя новые"""
    try:
        cert_file, key_file = generate_self_signed_cert()
        return (str(cert_file), str(key_file))
    except Exception as e:
        logger = LogManager.get_logger('ssl')
        logger.info(f"Ошибка работы с SSL сертификатами: {e}")
        raise
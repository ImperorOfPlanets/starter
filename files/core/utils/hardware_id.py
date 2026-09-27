"""
Сбор аппаратных идентификаторов устройства для fingerprint.
Кросс-платформенный: Windows (WMI), Linux (/sys, dmidecode), macOS (ioreg, system_profiler).
При невозможности получить компонент — использует fallback.
"""

import hashlib
import platform
import subprocess
import os
from typing import Dict, Optional


def _run_cmd(cmd: list, timeout: int = 5) -> Optional[str]:
    """Запустить команду и вернуть stdout или None при ошибке."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _read_file(path: str, timeout: int = 2) -> Optional[str]:
    """Прочитать файл (для /sys/class/dmi/id/*)."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            value = f.read().strip()
            if value and value != 'To Be Filled By O.E.M.':
                return value
    except Exception:
        pass
    return None


# ==================== Windows ====================

def _wmi_query(wmi_class: str, field: str) -> Optional[str]:
    """Запрос WMI через powershell."""
    cmd = [
        'powershell', '-NoProfile', '-Command',
        f'(Get-WmiObject {wmi_class}).{field}'
    ]
    return _run_cmd(cmd)


def _get_cpu_id_windows() -> Optional[str]:
    return _wmi_query('win32_Processor', 'ProcessorId')


def _get_motherboard_serial_windows() -> Optional[str]:
    return _wmi_query('win32_BaseBoard', 'SerialNumber')


def _get_disk_serial_windows() -> Optional[str]:
    # Берём серийный номер первого固定ного диска
    cmd = [
        'powershell', '-NoProfile', '-Command',
        "(Get-WmiObject win32_DiskDrive | Where-Object {$_.MediaType -eq 'Fixed hard disk media'} | Select-Object -First 1).SerialNumber"
    ]
    return _run_cmd(cmd)


def _get_bios_serial_windows() -> Optional[str]:
    return _wmi_query('win32_BIOS', 'SerialNumber')


# ==================== Linux ====================

def _get_cpu_id_linux() -> Optional[str]:
    # /proc/cpuinfo → Serial (если есть)
    serial = _read_file('/proc/cpuinfo')
    if serial:
        for line in serial.split('\n'):
            if 'Serial' in line or 'serial' in line:
                value = line.split(':')[-1].strip()
                if value and value != '00000000':
                    return value
    # Fallback: dmidecode
    output = _run_cmd(['dmidecode', '-s', 'processor-id'])
    if output:
        return output
    return None


def _get_motherboard_serial_linux() -> Optional[str]:
    serial = _read_file('/sys/class/dmi/id/board_serial')
    if serial:
        return serial
    output = _run_cmd(['dmidecode', '-s', 'baseboard-serial-number'])
    if output:
        return output
    return None


def _get_disk_serial_linux() -> Optional[str]:
    # Пробуем /sys/block/*/serial
    for dev in ['sda', 'nvme0n1', 'vda', 'hda']:
        serial = _read_file(f'/sys/block/{dev}/serial')
        if serial:
            return serial
    # Fallback: lsblk
    output = _run_cmd(['lsblk', '-d', '-o', 'SERIAL', '-n', '-J'])
    if output:
        try:
            import json
            data = json.loads(output)
            for device in data.get('blockdevices', []):
                serial = device.get('serial')
                if serial and serial != '':
                    return serial
        except Exception:
            pass
    return None


def _get_bios_serial_linux() -> Optional[str]:
    serial = _read_file('/sys/class/dmi/id/bios_serial')
    if serial:
        return serial
    output = _run_cmd(['dmidecode', '-s', 'bios-version'])
    if output:
        return output
    return None


# ==================== macOS ====================

def _ioreg_value(key: str) -> Optional[str]:
    """Получить значение из ioreg."""
    output = _run_cmd(['ioreg', '-c', 'IOPlatformExpertDevice', '-d', '2'])
    if output:
        for line in output.split('\n'):
            if f'"{key}"' in line:
                # Формат: "key" = "value" или "key" = <value>
                parts = line.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip().strip('"')
                    if value and value != 'null':
                        return value
    return None


def _get_cpu_id_macos() -> Optional[str]:
    # IOPlatformUUID на macOS уникален для платформы
    return _ioreg_value('IOPlatformUUID')


def _get_motherboard_serial_macos() -> Optional[str]:
    output = _run_cmd(['ioreg', '-c', 'IOPlatformExpertDevice', '-d', '2'])
    if output:
        for line in output.split('\n'):
            if '"serial-number"' in line.lower() or '"board-serial"' in line.lower():
                parts = line.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip().strip('"')
                    if value:
                        return value
    return None


def _get_disk_serial_macos() -> Optional[str]:
    output = _run_cmd(['diskutil', 'info', 'disk0'])
    if output:
        for line in output.split('\n'):
            if 'Serial Number' in line or 'Serial (NTFS)' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    value = parts[1].strip()
                    if value:
                        return value
    return None


def _get_bios_serial_macos() -> Optional[str]:
    output = _run_cmd(['ioreg', '-c', 'IOPlatformExpertDevice', '-d', '2'])
    if output:
        for line in output.split('\n'):
            if '"serial-number"' in line.lower():
                parts = line.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip().strip('"')
                    if value:
                        return value
    return None


# ==================== Публичный API ====================

def get_hardware_ids() -> Dict[str, Optional[str]]:
    """
    Собрать аппаратные идентификаторы устройства.
    Возвращает словарь с компонентами или None если не удалось.
    """
    system = platform.system()

    if system == 'Windows':
        return {
            'cpu_id': _get_cpu_id_windows(),
            'motherboard_serial': _get_motherboard_serial_windows(),
            'disk_serial': _get_disk_serial_windows(),
            'bios_serial': _get_bios_serial_windows(),
        }
    elif system == 'Linux':
        return {
            'cpu_id': _get_cpu_id_linux(),
            'motherboard_serial': _get_motherboard_serial_linux(),
            'disk_serial': _get_disk_serial_linux(),
            'bios_serial': _get_bios_serial_linux(),
        }
    elif system == 'Darwin':
        return {
            'cpu_id': _get_cpu_id_macos(),
            'motherboard_serial': _get_motherboard_serial_macos(),
            'disk_serial': _get_disk_serial_macos(),
            'bios_serial': _get_bios_serial_macos(),
        }
    else:
        return {
            'cpu_id': None,
            'motherboard_serial': None,
            'disk_serial': None,
            'bios_serial': None,
        }


def get_device_fingerprint() -> str:
    """
    Сформировать fingerprint устройства.
    
    Приоритет:
    1. Hardware ID (cpu + motherboard + disk + bios) — стабильный
    2. Fallback: hostname + mac + path — хрупкий, но работает всегда
    
    Возвращает SHA-256 hex digest (32 символа).
    """
    hw = get_hardware_ids()

    # Проверяем, сколько компонентов удалось получить
    available = [v for v in hw.values() if v]

    if len(available) >= 2:
        # Достаточно hardware ID — используем их
        fingerprint_data = ':'.join([
            hw.get('cpu_id') or '',
            hw.get('motherboard_serial') or '',
            hw.get('disk_serial') or '',
            hw.get('bios_serial') or '',
        ])
        source = 'hardware_ids'
    else:
        # Fallback на старый вариант
        import socket
        import uuid
        from files.core.utils.globalVars_utils import get_global

        hostname = socket.gethostname()
        mac_address = "unknown"
        try:
            mac_address = ':'.join([
                '{:02x}'.format((uuid.getnode() >> i) & 0xff)
                for i in range(0, 2 * 6, 2)
            ][::-1])
        except Exception:
            pass
        starter_path = str(get_global('starter_path', ''))

        fingerprint_data = f"{hostname}:{mac_address}:{starter_path}"
        source = 'fallback'

    fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

    return fingerprint


def get_hardware_info_display() -> Dict[str, str]:
    """
    Получить информацию об оборудовании для отображения пользователю.
    Используется на экране согласия / в логах.
    """
    hw = get_hardware_ids()
    system = platform.system()

    return {
        'os': system,
        'cpu_id': hw.get('cpu_id') or 'N/A',
        'motherboard_serial': hw.get('motherboard_serial') or 'N/A',
        'disk_serial': hw.get('disk_serial') or 'N/A',
        'bios_serial': hw.get('bios_serial') or 'N/A',
    }

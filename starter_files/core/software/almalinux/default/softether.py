from starter_files.core.base_module import BaseModule
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from starter_files.core.utils.globalVars_utils import get_global, set_global
from starter_files.core.utils.loader_utils import get
import platform
import logging
import subprocess
import os
import time

logger = logging.getLogger('softether_oss')

class SoftetherModule(BaseModule):
    """Реализация для установки SoftEther VPN Client"""

    def return_commands_install_softether() -> List[str]:
        """Возвращает команды для установки SoftEther VPN на AlmaLinux"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        prefix = "sudo " if (not is_root and use_sudo) else ""
        tmp_dir = "/app/tmp"
        
        return [
            # Подготовка временной директории
            f"{prefix}mkdir -p {tmp_dir}",
            f"{prefix}chmod 777 {tmp_dir}",
            
            # Установка зависимостей
            f"{prefix}yum -y groupinstall 'Development Tools'",
            f"{prefix}yum -y install epel-release",
            f"{prefix}yum -y install cmake ncurses-devel openssl-devel readline-devel zlib-devel",
            
            # Клонирование репозитория (официальный репозиторий Stable версии)
            f"git clone https://github.com/SoftEtherVPN/SoftEtherVPN_Stable.git {tmp_dir}/SoftEtherVPN || true",
            
            # Сборка и установка (согласно официальной инструкции)
            f"cd {tmp_dir}/SoftEtherVPN && "
            "git submodule init && "
            "git submodule update && "
            "./configure && "
            "make && "
            f"{prefix}make install",
            
            # Очистка (удаляем только содержимое)
            f"{prefix}rm -rf {tmp_dir}/SoftEtherVPN"
        ]
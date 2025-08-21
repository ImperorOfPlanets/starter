from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class KnockingModule(BaseModule):

    @staticmethod
    def return_commands_install_knockd() -> List[str]:
        """Возвращает список команд для установки port knocking (knockd)"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        
        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""

        commands = [
            # Установка EPEL-репозитория
            f"{prefix}yum install -y epel-release",
            
            # Установка knock-server из EPEL
            f"{prefix}yum install -y knock-server",
            
            # Включение и запуск службы
            f"{prefix}systemctl enable knockd",
            f"{prefix}systemctl start knockd",
            
            # Проверка статуса службы
            f"{prefix}systemctl status knockd --no-pager"
        ]
        return commands
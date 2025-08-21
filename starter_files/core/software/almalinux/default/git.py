from typing import List

from starter_files.core.base_module import BaseModule
from starter_files.core.utils.globalVars_utils import get_global

class GitModule(BaseModule):
    @staticmethod
    def return_commands_install_git() -> List[str]:
        """Возвращает список команд для установки Git"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        
        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""

        if not is_root:
            prefix = "sudo "  # Всегда используем sudo для не-root
        
        commands = [
            f"{prefix}yum install -y git"  # Для AlmaLinux/CentOS/RHEL
        ]
        return commands
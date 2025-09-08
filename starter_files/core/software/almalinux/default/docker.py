from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class DockerModule(BaseModule):

    @staticmethod
    def return_commands_install_docker() -> List[str]:
        """Возвращает список команд для установки только Docker"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        
        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""
        
        commands = [
            f"{prefix}yum install -y yum-utils",
            f"{prefix}yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
            f"{prefix}yum install -y docker-ce docker-ce-cli containerd.io",
        ]
        return commands

    @staticmethod
    def return_commands_install_compose() -> List[str]:
        """Возвращает список команд для установки Docker Compose"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')
        
        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""
        
        commands = [
            # Современные дистрибутивы — через плагин
            f"{prefix}yum install -y docker-compose-plugin",
            # Для совместимости можно добавить бинарник (если нужна старая версия)
            # f"{prefix}curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)\" -o /usr/local/bin/docker-compose",
            # f"{prefix}chmod +x /usr/local/bin/docker-compose",
        ]
        return commands

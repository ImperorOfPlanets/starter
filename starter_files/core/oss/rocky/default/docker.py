from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class DockerModule(BaseModule):

    @staticmethod
    def return_commands_install() -> List[str]:
        """Возвращает список команд для установки Docker в Rocky Linux"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')

        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""

        commands = [
            f"{prefix}dnf -y install dnf-plugins-core",
            f"{prefix}dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
            f"{prefix}dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
        ]

        usermod_prefix = "sudo " if not is_root else ""
        commands.append(f"{usermod_prefix}usermod -aG docker $USER")

        return commands

from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class DockerModule(BaseModule):

    @staticmethod
    def return_commands_install() -> List[str]:
        """Возвращает список команд для установки Docker в Fedora"""
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
            f"{prefix}dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo",
            f"{prefix}dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
        ]

        usermod_prefix = "sudo " if not is_root else ""
        commands.append(f"{usermod_prefix}usermod -aG docker $USER")

        return commands

    @staticmethod
    def return_commands_start() -> List[str]:
        """Возвращает команды для запуска Docker"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')

        prefix = ""
        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "

        return [
            f"{prefix}systemctl enable docker",
            f"{prefix}systemctl start docker"
        ]

    @staticmethod
    def check_docker_running() -> bool:
        """Проверяет, запущен ли Docker"""
        try:
            import subprocess
            result = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
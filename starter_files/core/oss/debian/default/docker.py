from starter_files.core.base_module import BaseModule

from typing import List

from starter_files.core.utils.globalVars_utils import get_global

class DockerModule(BaseModule):

    @staticmethod
    def return_commands_install() -> List[str]:
        """Возвращает список команд для установки Docker в Debian/Ubuntu"""
        is_root = get_global('is_root')
        use_sudo = get_global('use_sudo')

        if not is_root and use_sudo:
            prefix = "sudo "
        elif not is_root:
            prefix = "sudo "
        else:
            prefix = ""

        commands = [
            f"{prefix}apt update",
            f"{prefix}apt install -y apt-transport-https ca-certificates curl gnupg lsb-release",
            f"{prefix}curl -fsSL https://download.docker.com/linux/debian/gpg | {prefix}gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg",
            f"{prefix}echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable\" | {prefix}tee /etc/apt/sources.list.d/docker.list > /dev/null",
            f"{prefix}apt update",
            f"{prefix}apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
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
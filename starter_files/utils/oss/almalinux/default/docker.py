from typing import List

from starter_files.utils.globalVars_utils import get_global

class DockerModule:
    @staticmethod
    def check() -> bool:
        return True

    @staticmethod
    def return_commands_install() -> List[str]:
        """Возвращает список команд для установки Docker на AlmaLinux"""
        commands = [
            "sudo yum install -y yum-utils",
            "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
            "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
            "sudo systemctl start docker",
            "sudo systemctl enable docker",
            "sudo usermod -aG docker $USER"
        ]
        return commands

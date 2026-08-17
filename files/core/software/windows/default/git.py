from typing import List
from files.core.base_module import BaseModule


class GitModule(BaseModule):
    """Windows Git installation via winget"""

    @staticmethod
    def return_commands_install_git() -> List[str]:
        """Returns commands to install Git on Windows via winget"""
        return [
            'winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements'
        ]

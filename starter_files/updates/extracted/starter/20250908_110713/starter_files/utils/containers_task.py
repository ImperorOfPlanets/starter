from starter_files.untils.docker_utils import DockerUtils

class ContainersTask:
    def execute(self):
        if not DockerUtils.check_installed():
            raise Exception("Docker не установлен")
        
        # Ваша логика проверки контейнеров
        print("Проверка контейнеров...")
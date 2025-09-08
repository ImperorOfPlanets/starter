import os
import sys
import platform
from pathlib import Path
from starter_files.utils.docker_utils import DockerUtils
from starter_files.utils.fs_utils import FSUtils
from starter_files.utils.logger import logger

class InteractiveMode:
    def __init__(self):
        self.registry_url = "gitflic.myidon.site:80"
        self.script_path = Path(__file__).resolve().parent.parent / "starter.py"

    def run(self):
        """Основной метод запуска интерактивного режима"""
        self._show_system_info()
        self._check_dependencies()
        self._show_main_menu()

    def _show_system_info(self):
        """Вывод системной информации"""
        print("\n=== СИСТЕМНАЯ ИНФОРМАЦИЯ ===")
        print(f"ОС: {platform.system()} {platform.version()}")
        print(f"Python: {platform.python_version()}")
        
        ips = FSUtils.get_ip_addresses()
        valid_ips = [ip for ip in ips if FSUtils.is_valid_network(ip)]
        print(f"IP-адреса: {', '.join(valid_ips) if valid_ips else 'не обнаружены'}")

    def _check_dependencies(self):
        """Проверка необходимых зависимостей"""
        print("\n=== ПРОВЕРКА ЗАВИСИМОСТЕЙ ===")
        if not DockerUtils.check_installed():
            print("[Ошибка] Docker не установлен!")
        elif not DockerUtils.check_compose():
            print("[Ошибка] Docker Compose не установлен!")

        # Проверка авторизации в Docker Registry
        if DockerUtils.check_registry_auth(self.registry_url):
            print(f"[Статус] Авторизация в Docker Registry ({self.registry_url}) успешна")
        else:
            print(f"[Внимание] Не авторизован в Docker Registry. Выполните: docker login {self.registry_url}")

    def _show_main_menu(self):
        """Главное меню приложения"""
        while True:
            print("\n=== ГЛАВНОЕ МЕНЮ ===")
            menu_items = [
                "1. Собрать образы и отправить в реестр",
                "2. Обновить образы из реестра",
                "3. Управление службой",
                "4. Проверить обновления",
                "5. Настроить автозагрузку",
                "0. Выход"
            ]
            
            print("\n".join(menu_items))
            choice = input("\nВыберите действие: ").strip()

            if choice == '1':
                self._build_and_push_images()
            elif choice == '2':
                self._pull_images()
            elif choice == '3':
                self._manage_service()
            elif choice == '4':
                self._check_updates()
            elif choice == '5':
                self._manage_autostart()
            elif choice == '0':
                sys.exit(0)
            else:
                print("Неверный ввод, попробуйте снова")

    
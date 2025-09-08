from starter_files.core.base_module import BaseModule
import json
import logging
import platform
import subprocess
import re
from pathlib import Path
import os
import time
from typing import Dict, List, Optional
from starter_files.core.utils.loader_utils import get
from starter_files.core.utils.globalVars_utils import get_global, set_global
from datetime import datetime

logger = logging.getLogger('docker_oss')

class DockerModule(BaseModule):
    """Реализация Docker утилит"""

    @staticmethod
    def check_docker_installed() -> bool:
        """Проверяет установлен ли Docker и возвращает статус"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def check_docker_compose_installed():
        """Проверка наличия Docker Compose (v1 и v2)"""
        try:
            # Проверка новой версии (v2)
            subprocess.check_output(["docker", "compose", "version"], stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            try:
                # Проверка старой версии (v1)
                subprocess.check_output(["docker-compose", "--version"], stderr=subprocess.DEVNULL)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                return False

    @staticmethod
    def install_docker(log_file_path: str) -> Dict[str, str]:
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting Docker installation...")
                
                commands = get("docker","return_commands_install_docker")
                
                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result
                
                # ПРЯМО ЗДЕСЬ ОБНОВЛЯЕМ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
                time.sleep(2)
                docker_installed = DockerModule.check_docker_installed()
                set_global('docker_installed', docker_installed)
                
                if docker_installed:
                    log("Docker installed successfully! Please restart your session.")
                    result['message'] = "Docker installed successfully! Please restart your session."
                else:
                    log("Installation completed but Docker not detected. Try restarting your system.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker not detected. Try restarting your system."
                
                # Добавляем маркер завершения
                log("INSTALL FINISH!")
        
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            try:
                with open(log_file_path, 'a') as f:
                    f.write(error_msg + '\n')
                    f.write("INSTALL FINISH!\n")
            except:
                logger.exception("Failed to write error to log file")
            
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("Docker installation error")
        
        return result

    @staticmethod
    def install_docker_compose(log_file_path: str) -> Dict[str, str]:
        result = {'status': 'success', 'message': '', 'logs': []}
        
        try:
            with open(log_file_path, 'w') as log_file:
                def log(message):
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {message}"
                    log_file.write(log_entry + '\n')
                    log_file.flush()
                    result['logs'].append(log_entry)
                    logger.info(log_entry)
                
                log("Starting Docker Compose installation...")
                
                commands = get("docker","return_commands_install_compose")
                
                for cmd in commands:
                    log(f"Executing: {cmd}")
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            log(line.strip())
                    
                    return_code = process.wait()
                    if return_code != 0:
                        log(f"Command failed with exit code {return_code}")
                        result['status'] = 'error'
                        result['message'] = f"Command failed: {cmd}"
                        return result
                
                # ПРЯМО ЗДЕСЬ ОБНОВЛЯЕМ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
                time.sleep(2)
                docker_compose_installed = DockerModule.check_docker_compose_installed()
                set_global('docker_compose_installed', docker_compose_installed)
                
                if docker_compose_installed:
                    log("Docker Compose installed successfully!")
                    result['message'] = "Docker Compose installed successfully!"
                else:
                    log("Installation completed but Docker Compose not detected.")
                    result['status'] = 'warning'
                    result['message'] = "Installation completed but Docker Compose not detected."
                
                # Добавляем маркер завершения
                log("INSTALL FINISH!")
        
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            try:
                with open(log_file_path, 'a') as f:
                    f.write(error_msg + '\n')
                    f.write("INSTALL FINISH!\n")
            except:
                logger.exception("Failed to write error to log file")
            
            result['status'] = 'error'
            result['message'] = error_msg
            logger.exception("Docker Compose installation error")
        
        return result

    @staticmethod
    def check_dockerfiles(docker_dir: str) -> bool:
        """Проверка наличия необходимых Dockerfile"""
        required = [
            os.path.join("dockerfiles", "Dockerfile_other"),
            os.path.join("dockerfiles", "Dockerfile_php")
        ]
        for path in required:
            if not (Path(docker_dir) / path).exists():
                return False
        return True

    @staticmethod
    def replace_env_variables(content: str, env_vars: Dict[str, str]) -> str:
        """Заменяет ${PROJECTNAME} на значение из env_vars"""
        def replace_match(match):
            return env_vars.get("PROJECTNAME", match.group(0))
        
        return re.sub(
            r'\$\{PROJECTNAME\}',
            replace_match,
            content
        )

    @staticmethod
    def process_service_blocks(content: str, enabled_services: List[str], env_vars: Dict[str, str]) -> str:
        """Обрабатывает блоки сервисов, оставляя только разрешенные"""
        pattern = re.compile(
            r'### START (.+?) ###(.*?)### END \1 ###',
            re.DOTALL
        )
        
        def replace_block(match):
            service_name = match.group(1).strip().upper()
            block_content = match.group(2)
            
            if service_name in enabled_services:
                replaced_content = DockerModule.replace_env_variables(block_content, env_vars)
                return f"### START {service_name} ###{replaced_content}### END {service_name} ###"
            return ''
        
        return pattern.sub(replace_block, content)

    @staticmethod
    def generate_compose(docker_dir: str, env_vars: Dict[str, str], pull_from_registry: bool = False) -> bool:
        """Генерирует docker-compose.yml на основе примера"""
        docker_dir = Path(docker_dir)
        compose_example = docker_dir / "docker-compose.example"
        compose_output = docker_dir / "docker-compose.yml"
        
        try:
            content = compose_example.read_text(encoding='utf-8')
            if pull_from_registry:
                content = re.sub(
                    r'\n\s+build:.?dockerfile:.?\n',
                    '\n',
                    content,
                    flags=re.DOTALL
                )
            enabled_services = [
                s.strip().upper() 
                for s in env_vars.get("ENABLED_SERVICES", "").split(",") 
                if s.strip()
            ]
            content = DockerModule.process_service_blocks(content, enabled_services, env_vars)
            content = DockerModule.replace_env_variables(content, env_vars)
            compose_output.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"Error generating compose: {str(e)}")
            return False

    @staticmethod
    def get_container_status(container_name: str) -> Optional[Dict]:
        """Получение статуса контейнера"""
        try:
            result = subprocess.run(
                ['docker', 'inspect', '--format', '{{json .}}', container_name],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Error getting container status: {str(e)}")
            return None
        
    @staticmethod
    def manage_container(container_name: str, action: str) -> bool:
        """Управление контейнером (start/stop/restart)"""
        try:
            subprocess.run(
                ['docker', action, container_name],
                check=True
            )
            return True
        except Exception as e:
            logger.error(f"Error managing container: {str(e)}")
            return False

    @staticmethod
    def get_docker_info() -> Dict:
        """Собирает информацию о Docker"""

        info = {
            'version': 'N/A',
            'containers': {
                'total': 0,
                'running': 0,
                'paused': 0,
                'stopped': 0
            },
            'images': 0,
            'system': {
                'cpu_usage': 'N/A',
                'memory_usage': 'N/A',
                'disk_usage': 'N/A'
            },
            'compose': {
                'projects': 0,
                'services': 0
            }
        }

        try:
            # Версия Docker
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                info['version'] = result.stdout.strip()

            # Статистика контейнеров
            result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.State}}'], capture_output=True, text=True)
            if result.returncode == 0:
                states = result.stdout.splitlines()
                info['containers']['total'] = len(states)
                info['containers']['running'] = states.count('running')
                info['containers']['paused'] = states.count('paused')
                info['containers']['stopped'] = states.count('exited') + states.count('created')

            # Количество образов
            result = subprocess.run(['docker', 'images', '-q'], capture_output=True, text=True)
            if result.returncode == 0:
                info['images'] = len(result.stdout.splitlines())

            # Статистика системы Docker
            result = subprocess.run(['docker', 'system', 'df', '--format', '{{json .}}'], capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    system_data = json.loads(result.stdout)
                    info['system']['disk_usage'] = system_data.get('Size', 'N/A')
                except json.JSONDecodeError:
                    pass

            # Статистика использования ресурсов
            result = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{json .}}'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                cpu_total = 0.0
                mem_total = 0.0
                count = 0
                for line in result.stdout.splitlines():
                    try:
                        stats = json.loads(line)
                        cpu_total += float(stats['CPUPerc'].replace('%', ''))
                        mem_total += float(stats['MemPerc'].replace('%', ''))
                        count += 1
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                if count > 0:
                    info['system']['cpu_usage'] = f"{cpu_total/count:.1f}%"
                    info['system']['memory_usage'] = f"{mem_total/count:.1f}%"

            # Информация о Docker Compose
            try:
                result = subprocess.run(['docker-compose', 'ls', '--format', 'json'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    projects = json.loads(result.stdout)
                    info['compose']['projects'] = len(projects)
                    info['compose']['services'] = sum(len(p.get('Services', [])) for p in projects)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error collecting Docker info: {str(e)}")

        return info

    @staticmethod
    def get_containers(all: bool = False) -> List[Dict]:
        """Получает список контейнеров"""

        containers = []
        try:
            format_str = '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.RunningFor}}|{{.Size}}'
            cmd = ['docker', 'ps', '--format', format_str]
            if all:
                cmd.append('-a')
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 7:
                        containers.append({
                            'id': parts[0],
                            'name': parts[1],
                            'image': parts[2],
                            'status': parts[3],
                            'ports': parts[4],
                            'running_for': parts[5],
                            'size': parts[6]
                        })
        except Exception as e:
            logger.error(f"Error getting containers: {str(e)}")
        return containers

    @staticmethod
    def get_images() -> List[Dict]:
        """Получает список образов"""
        images = []
        try:
            format_str = '{{.ID}}|{{.Repository}}|{{.Tag}}|{{.CreatedSince}}|{{.CreatedAt}}|{{.Size}}'
            result = subprocess.run(['docker', 'images', '--format', format_str], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 6:
                        images.append({
                            'id': parts[0],
                            'repository': parts[1],
                            'tag': parts[2],
                            'created_since': parts[3],
                            'created_at': parts[4],
                            'size': parts[5]
                        })
        except Exception as e:
            logger.error(f"Error getting images: {str(e)}")
        return images

    @staticmethod
    def get_logs(container_id: str, tail: int = 100) -> str:
        """Получает логи контейнера"""
        try:
            result = subprocess.run(['docker', 'logs', '--tail', str(tail), container_id], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            logger.error(f"Error getting logs: {str(e)}")
        return ""

    @staticmethod
    def get_networks() -> List[Dict]:
        """Получает список сетей"""
        networks = []
        try:
            format_str = '{{.ID}}|{{.Name}}|{{.Driver}}|{{.Scope}}|{{.IPv6}}|{{.Internal}}|{{.Created}}'
            result = subprocess.run(['docker', 'network', 'ls', '--format', format_str], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 7:
                        networks.append({
                            'id': parts[0],
                            'name': parts[1],
                            'driver': parts[2],
                            'scope': parts[3],
                            'ipv6': parts[4],
                            'internal': parts[5],
                            'created': parts[6]
                        })
        except Exception as e:
            logger.error(f"Error getting networks: {str(e)}")
        return networks

    @staticmethod
    def get_volumes() -> List[Dict]:
        """Получает список томов"""
        volumes = []
        try:
            format_str = '{{.Name}}|{{.Driver}}|{{.Scope}}|{{.Mountpoint}}|{{.Labels}}|{{.CreatedAt}}'
            result = subprocess.run(['docker', 'volume', 'ls', '--format', format_str], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    parts = line.split('|')
                    if len(parts) >= 6:
                        volumes.append({
                            'name': parts[0],
                            'driver': parts[1],
                            'scope': parts[2],
                            'mountpoint': parts[3],
                            'labels': parts[4],
                            'created_at': parts[5]
                        })
        except Exception as e:
            logger.error(f"Error getting volumes: {str(e)}")
        return volumes

    @staticmethod
    def container_action(data: Dict) -> Dict:
        """Выполняет действие с контейнером (старт/стоп и т.д.)"""
        action = data.get('action')
        container_id = data.get('container_id')
        
        if not action or not container_id:
            return {'status': 'error', 'message': 'Invalid parameters'}
        
        try:
            if action == 'start':
                subprocess.run(['docker', 'start', container_id], check=True)
                return {'status': 'success', 'message': 'Container started'}
            elif action == 'stop':
                subprocess.run(['docker', 'stop', container_id], check=True)
                return {'status': 'success', 'message': 'Container stopped'}
            elif action == 'restart':
                subprocess.run(['docker', 'restart', container_id], check=True)
                return {'status': 'success', 'message': 'Container restarted'}
            elif action == 'remove':
                subprocess.run(['docker', 'rm', container_id], check=True)
                return {'status': 'success', 'message': 'Container removed'}
            else:
                return {'status': 'error', 'message': 'Invalid action'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Container action failed: {str(e)}")
            return {'status': 'error', 'message': f"Action failed: {str(e)}"}

    @staticmethod
    def image_action(data: Dict) -> Dict:
        """Выполняет действие с образом (удаление и т.д.)"""
        action = data.get('action')
        image_id = data.get('image_id')
        
        if not action or not image_id:
            return {'status': 'error', 'message': 'Invalid parameters'}
        
        try:
            if action == 'remove':
                subprocess.run(['docker', 'rmi', image_id], check=True)
                return {'status': 'success', 'message': 'Image removed'}
            else:
                return {'status': 'error', 'message': 'Invalid action'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Image action failed: {str(e)}")
            return {'status': 'error', 'message': f"Action failed: {str(e)}"}

    @staticmethod
    def restart_docker() -> Dict:
        """Перезапускает Docker сервис"""
        try:
            if platform.system() == 'Windows':
                subprocess.run(['net', 'stop', 'docker'], check=True)
                subprocess.run(['net', 'start', 'docker'], check=True)
            else:
                subprocess.run(['sudo', 'systemctl', 'restart', 'docker'], check=True)
            return {'status': 'success', 'message': 'Docker restarted successfully'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart Docker: {str(e)}")
            return {'status': 'error', 'message': f"Failed to restart Docker: {str(e)}"}

    @staticmethod
    def prune_system() -> Dict:
        """Очищает неиспользуемые объекты Docker"""

        try:
            subprocess.run(['docker', 'system', 'prune', '-f'], check=True)
            return {'status': 'success', 'message': 'System pruned successfully'}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to prune system: {str(e)}")
            return {'status': 'error', 'message': f"Failed to prune system: {str(e)}"}

    @staticmethod
    def set_globals():
        """Устанавливает глобальные для DOCKER"""
        docker_installed = get('docker',"check_docker_installed")
        logger.info("Переменная docker_installed")
        logger.info(docker_installed)

        docker_compose_installed = get('docker',"check_docker_compose_installed")
        logger.info("Переменная docker_compose_installed")
        logger.info(docker_compose_installed)

        
        # Устанавливаем глобальные переменные
        set_global('docker_installed', docker_installed)
        set_global('docker_compose_installed', docker_compose_installed)
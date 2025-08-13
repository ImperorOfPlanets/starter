import json
import logging
import platform
import subprocess

from typing import Dict, List, Optional

from starter_files.utils.i18n_utils import t

class DockerModule:
    """Базовая реализация Docker утилит для неподдерживаемых ОС"""
    
    @staticmethod
    def check_installed() -> bool:
        """Проверяет установлен ли Docker и возвращает статус"""
        import subprocess
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
    def check_docker_compose_installed() -> bool:
        """Проверяет установлен ли Docker Compose и возвращает статус"""
        import subprocess
        try:
            subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    
    @staticmethod
    def check_dockerfiles(docker_dir: str) -> bool:
        """Проверка наличия необходимых Dockerfile"""
        from pathlib import Path
        import os

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
        import re

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
        import re

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
        from pathlib import Path
        import re

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
        except Exception:
            return False

    
        @staticmethod
        def get_container_status(container_name: str) -> Optional[Dict]:
            """Получение статуса контейнера"""
            logging.warning("Получение статуса контейнера не поддерживается")
            return None
        
        @staticmethod
        def manage_container(container_name: str, action: str) -> bool:
            """Управление контейнером (start/stop/restart)"""
            logging.warning(f"Управление контейнером ({action}) не поддерживается")
            return False

    def get_docker_info():
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
            # Получаем версию Docker
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                info['version'] = result.stdout.strip()

            # Получаем статистику контейнеров
            result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.State}}'], capture_output=True, text=True)
            if result.returncode == 0:
                states = result.stdout.splitlines()
                info['containers']['total'] = len(states)
                info['containers']['running'] = states.count('running')
                info['containers']['paused'] = states.count('paused')
                info['containers']['stopped'] = states.count('exited') + states.count('created')

            # Получаем количество образов
            result = subprocess.run(['docker', 'images', '-q'], capture_output=True, text=True)
            if result.returncode == 0:
                info['images'] = len(result.stdout.splitlines())

            # Получаем статистику системы Docker
            result = subprocess.run(['docker', 'system', 'df', '--format', '{{json .}}'], capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    system_data = json.loads(result.stdout)
                    info['system']['disk_usage'] = system_data.get('Size', 'N/A')
                except json.JSONDecodeError:
                    pass

            # Получаем статистику использования ресурсов
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

            # Получаем информацию о Docker Compose
            try:
                result = subprocess.run(['docker-compose', 'ls', '--format', 'json'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    projects = json.loads(result.stdout)
                    info['compose']['projects'] = len(projects)
                    info['compose']['services'] = sum(len(p.get('Services', [])) for p in projects)
            except:
                pass

        except Exception as e:
            print(f"Error collecting Docker info: {str(e)}")

        return info

    def get_containers(all=False):
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
            print(f"Error getting containers: {str(e)}")
        return containers

    def get_images():
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
            print(f"Error getting images: {str(e)}")
        return images

    def get_logs(container_id, tail=100):
        """Получает логи контейнера"""
        try:
            result = subprocess.run(['docker', 'logs', '--tail', str(tail), container_id], 
                                capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            print(f"Error getting logs: {str(e)}")
        return ""

    def get_networks():
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
            print(f"Error getting networks: {str(e)}")
        return networks

    def get_volumes():
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
            print(f"Error getting volumes: {str(e)}")
        return volumes

    def container_action(data, session):
        """Выполняет действие с контейнером (старт/стоп и т.д.)"""
        action = data.get('action')
        container_id = data.get('container_id')
        
        if not action or not container_id:
            return {'status': 'error', 'message': t('invalid_parameters')}
        
        try:
            if action == 'start':
                subprocess.run(['docker', 'start', container_id], check=True)
                return {'status': 'success', 'message': t('container_started')}
            elif action == 'stop':
                subprocess.run(['docker', 'stop', container_id], check=True)
                return {'status': 'success', 'message': t('container_stopped')}
            elif action == 'restart':
                subprocess.run(['docker', 'restart', container_id], check=True)
                return {'status': 'success', 'message': t('container_restarted')}
            elif action == 'remove':
                subprocess.run(['docker', 'rm', container_id], check=True)
                return {'status': 'success', 'message': t('container_removed')}
            else:
                return {'status': 'error', 'message': t('invalid_action')}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f"{t('action_failed')}: {str(e)}"}

    def image_action(data, session):
        """Выполняет действие с образом (удаление и т.д.)"""
        action = data.get('action')
        image_id = data.get('image_id')
        
        if not action or not image_id:
            return {'status': 'error', 'message': t('invalid_parameters')}
        
        try:
            if action == 'remove':
                subprocess.run(['docker', 'rmi', image_id], check=True)
                return {'status': 'success', 'message': t('image_removed')}
            else:
                return {'status': 'error', 'message': t('invalid_action')}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': f"{t('action_failed')}: {str(e)}"}

    def restart_docker(data, session):
        """Перезапускает Docker сервис"""
        try:
            if platform.system() == 'Windows':
                subprocess.run(['net', 'stop', 'docker'], check=True)
                subprocess.run(['net', 'start', 'docker'], check=True)
            else:
                subprocess.run(['sudo', 'systemctl', 'restart', 'docker'], check=True)
            return {'status': 'success', 'message': t('docker_restarted_successfully')}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': t('failed_to_restart_docker') + f": {str(e)}"}

    def prune_system(data, session):
        """Очищает неиспользуемые объекты Docker"""
        try:
            subprocess.run(['docker', 'system', 'prune', '-f'], check=True)
            return {'status': 'success', 'message': t('system_pruned_successfully')}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': t('failed_to_prune_system') + f": {str(e)}"}
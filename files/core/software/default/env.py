"""
Модуль управления .env файлами проекта (локальными, не системными)
"""

from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional

from files.core.base_module import BaseModule
from files.core.utils.globalVars_utils import get_global, set_global
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger('env')

class EnvModule(BaseModule):
    """Модуль работы с .env файлами проекта"""
    
    @staticmethod
    def check() -> bool:
        return True
    
    @staticmethod
    def set_globals():
        """Устанавливает пути к .env файлам"""
        starter_path = get_global('starter_path')
        project_path = get_global('project_path')
        docker_path = get_global('docker_path')
        
        if starter_path:
            set_global('starter_env_path', starter_path / '.env')
            set_global('starter_env_example_path', starter_path / '.env.example')
        
        if docker_path:
            set_global('docker_env_path', docker_path / '.env')
            set_global('docker_env_example_path', docker_path / '.env.example')
        
        if project_path:
            set_global('project_env_path', project_path / '.env')
        
        logger.info(f"Starter env: {get_global('starter_env_path')}")
        if docker_path:
            logger.info(f"Docker env: {get_global('docker_env_path')}")
    
    @staticmethod
    def parse_env_content(content: str) -> Tuple[Dict[str, str], List[Union[str, Tuple[str, str]]]]:
        """Парсит содержимое .env файла, сохраняя структуру"""
        variables = {}
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                lines.append(line)
                continue
            
            if '=' in stripped:
                key, value = stripped.split('=', 1)
                key = key.strip()
                variables[key] = value.strip()
                lines.append((key, line))
            else:
                lines.append(line)
        
        return variables, lines
    
    @staticmethod
    def generate_env_content(vars_dict: Dict[str, str], 
                           template_lines: List[Union[str, Tuple[str, str]]],
                           preserve_custom: bool = True) -> str:
        """Генерирует содержимое .env файла с сохранением структуры"""
        result = []
        vars_to_add = vars_dict.copy()
        custom_vars = {}
        
        for line in template_lines:
            if isinstance(line, tuple):
                key, original_line = line
                if key in vars_to_add:
                    if '=' in original_line:
                        prefix = original_line.split('=', 1)[0]
                        new_line = f"{prefix}={vars_to_add.pop(key)}"
                    else:
                        new_line = f"{key}={vars_to_add.pop(key)}"
                    result.append(new_line)
                else:
                    result.append(original_line)
            else:
                result.append(line)
        
        if preserve_custom:
            custom_vars = {k: v for k, v in vars_dict.items() 
                          if k not in [l[0] for l in template_lines if isinstance(l, tuple)]}
            if custom_vars:
                result.append('\n# Custom variables')
                for key, value in custom_vars.items():
                    result.append(f"{key}={value}")
        
        return '\n'.join(result)
    
    @staticmethod
    def read_env_file(env_path: Path) -> Dict[str, str]:
        """Читает .env файл и возвращает словарь переменных"""
        if not env_path.exists():
            return {}
        
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        variables, _ = EnvModule.parse_env_content(content)
        return variables
    
    @staticmethod
    def write_env_file(env_path: Path, vars_dict: Dict[str, str], template_path: Path = None):
        """Записывает .env файл с сохранением структуры шаблона"""
        if template_path and template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            _, template_lines = EnvModule.parse_env_content(template_content)
            content = EnvModule.generate_env_content(vars_dict, template_lines)
        else:
            content = EnvModule.generate_env_content(vars_dict, [])
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def ensure_env_variables():
        """Обновляет .env файл в соответствии с .env.example"""
        example_path = get_global('starter_env_example_path')
        env_path = get_global('starter_env_path')
        
        if not example_path or not example_path.exists():
            return
        
        current_vars = EnvModule.read_env_file(env_path)
        with open(example_path, 'r', encoding='utf-8') as f:
            example_content = f.read()
        example_vars, example_lines = EnvModule.parse_env_content(example_content)
        
        merged_vars = {**example_vars, **current_vars}
        content = EnvModule.generate_env_content(merged_vars, example_lines)
        
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @staticmethod
    def get_env_var(key: str, default: str = None) -> Optional[str]:
        """Получает переменную из .env"""
        env_path = get_global('starter_env_path')
        if not env_path or not env_path.exists():
            return default
        
        vars_dict = EnvModule.read_env_file(env_path)
        return vars_dict.get(key, default)
    
    @staticmethod
    def set_env_var(key: str, value: str) -> bool:
        """Устанавливает переменную в .env"""
        env_path = get_global('starter_env_path')
        if not env_path:
            return False
        
        vars_dict = EnvModule.read_env_file(env_path)
        vars_dict[key] = value
        
        EnvModule.write_env_file(env_path, vars_dict)
        return True
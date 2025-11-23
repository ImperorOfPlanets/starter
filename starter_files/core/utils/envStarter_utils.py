from pathlib import Path
from typing import Dict, List, Tuple, Union
from starter_files.core.utils.globalVars_utils import get_global

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
        custom_vars = {k: v for k, v in vars_dict.items() if k not in [l[0] for l in template_lines if isinstance(l, tuple)]}
        if custom_vars:
            result.append('\n# Custom variables')
            for key, value in custom_vars.items():
                result.append(f"{key}={value}")
    
    return '\n'.join(result)

def read_env_file(env_path: Path) -> Dict[str, str]:
    """Читает .env файл и возвращает словарь переменных"""
    if not env_path.exists():
        return {}
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    variables, _ = parse_env_content(content)
    return variables

def write_env_file(env_path: Path, 
                  vars_dict: Dict[str, str], 
                  template_path: Path = None):
    """Записывает .env файл с сохранением структуры шаблона"""
    if template_path and template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        _, template_lines = parse_env_content(template_content)
        content = generate_env_content(vars_dict, template_lines)
    else:
        content = generate_env_content(vars_dict, [])
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)

def ensure_env_variables():
    """Обновляет .env файл в соответствии с .env.example"""
    script_path = get_global('script_pat')

    env_path = script_path / 'script_pat'
    logger.info('.env')
    
    env_example_path = script_path / '.env.example'
    logger.info(env_example_path)
    
    if not env_example_path.exists():
        return
    
    current_vars = read_env_file(env_path)
    with open(env_example_path, 'r', encoding='utf-8') as f:
        example_content = f.read()
    example_vars, example_lines = parse_env_content(example_content)
    
    merged_vars = {**example_vars, **current_vars}
    content = generate_env_content(merged_vars, example_lines)
    
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
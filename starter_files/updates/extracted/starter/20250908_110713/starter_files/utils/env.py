import re

def validate_env_file(env_path, allowed_empty=None):
    """
    Проверяет .env файл на наличие незаполненных переменных.
    Возвращает список пустых переменных, учитывая разрешенные пустые значения.
    
    :param env_path: Путь к .env файлу
    :param allowed_empty: Список разрешенных пустых переменных
    :return: Список незаполненных переменных
    """
    if allowed_empty is None:
        allowed_empty = ['ENABLED_SERVICES']
        
    empty_vars = []

    env_pattern = re.compile(
        r'^\s*'                             # Начальные пробелы
        r'(?!#)'                            # Игнорируем комментарии (строка не начинается с #)
        r'(?P<key>[A-Za-z_][A-Za-z0-9_]*)'  # Имя переменной
        r'\s*=\s*'                          # Разделитель =
        r'(?P<value>'                       # Значение:
            r'''(\s*                        # Пустые пробелы
                ("")?                       # Пустые кавычки ""
                |('')?                      # Или пустые кавычки ''
                |[^#\n]*                    # Любые символы кроме # и переноса
            )'''                         
        r')'                             
        r'\s*'                              # Пробелы в конце
        r'(?=\n|$)',                        # До конца строки или файла
        re.MULTILINE
    )

    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        for match in env_pattern.finditer(content):
            key = match.group('key')
            value = match.group('value').strip()
            
            if key not in allowed_empty:
                is_empty = (
                    not value 
                    or value in ('""', "''", "' '", '" "')
                    or (len(value.strip('"\'')) == 0)
                )
                
                if is_empty:
                    empty_vars.append(key)
                    
    return empty_vars
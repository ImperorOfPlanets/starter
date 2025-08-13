def get_service_status():
    """Получает статус сервиса для текущей ОС"""
    system = platform.system().lower()
    status = {
        'installed': False,
        'running': False,
        'enabled': False,
        'os': system
    }
    
    try:
        if system == 'windows':
            # Проверка для Windows
            result = subprocess.run(
                ['sc', 'query', SERVICE_NAME],
                capture_output=True,
                text=True,
                check=False
            )
            
            status['installed'] = 'SERVICE_NAME' in result.stdout
            if status['installed']:
                status['running'] = 'RUNNING' in result.stdout
                
                # Проверка автозагрузки
                start_type = subprocess.run(
                    ['sc', 'qc', SERVICE_NAME],
                    capture_output=True,
                    text=True,
                    check=False
                )
                status['enabled'] = 'AUTO_START' in start_type.stdout
                
        elif system == 'linux':
            # Проверка для systemd (современные Linux)
            result = subprocess.run(
                ['systemctl', 'is-active', SERVICE_NAME],
                capture_output=True,
                text=True,
                check=False
            )
            status['running'] = result.returncode == 0
            
            result = subprocess.run(
                ['systemctl', 'is-enabled', SERVICE_NAME],
                capture_output=True,
                text=True,
                check=False
            )
            status['enabled'] = result.returncode == 0
            status['installed'] = status['running'] or status['enabled']
            
        elif system == 'darwin':
            # Проверка для macOS (launchd)
            result = subprocess.run(
                ['launchctl', 'list', '|', 'grep', SERVICE_NAME],
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            status['installed'] = SERVICE_NAME in result.stdout
            status['running'] = status['installed']
            
            # Проверка автозагрузки
            result = subprocess.run(
                ['launchctl', 'print', f'gui/{os.getuid()}/{SERVICE_NAME}'],
                capture_output=True,
                text=True,
                check=False
            )
            status['enabled'] = 'enabled' in result.stdout.lower()
    
    except Exception as e:
        logger.error(f"Error checking service status: {str(e)}")
    
    return status

def service_action(data, session):
    """Выполняет действие с сервисом"""
    action = data.get('action')
    status = get_service_status()
    system = status['os']
    
    try:
        if system == 'windows':
            if action == 'start':
                subprocess.run(['sc', 'start', SERVICE_NAME], check=True)
            elif action == 'stop':
                subprocess.run(['sc', 'stop', SERVICE_NAME], check=True)
            elif action == 'restart':
                subprocess.run(['sc', 'stop', SERVICE_NAME], check=True)
                subprocess.run(['sc', 'start', SERVICE_NAME], check=True)
                
        elif system == 'linux':
            if action == 'start':
                subprocess.run(['systemctl', 'start', SERVICE_NAME], check=True)
            elif action == 'stop':
                subprocess.run(['systemctl', 'stop', SERVICE_NAME], check=True)
            elif action == 'restart':
                subprocess.run(['systemctl', 'restart', SERVICE_NAME], check=True)
            elif action == 'enable':
                subprocess.run(['systemctl', 'enable', SERVICE_NAME], check=True)
            elif action == 'disable':
                subprocess.run(['systemctl', 'disable', SERVICE_NAME], check=True)
                
        elif system == 'darwin':
            if action == 'start':
                subprocess.run(['launchctl', 'load', f'/Library/LaunchDaemons/{SERVICE_NAME}.plist'], check=True)
            elif action == 'stop':
                subprocess.run(['launchctl', 'unload', f'/Library/LaunchDaemons/{SERVICE_NAME}.plist'], check=True)
            elif action == 'restart':
                subprocess.run(['launchctl', 'unload', f'/Library/LaunchDaemons/{SERVICE_NAME}.plist'], check=True)
                subprocess.run(['launchctl', 'load', f'/Library/LaunchDaemons/{SERVICE_NAME}.plist'], check=True)
                
        return {'status': 'success', 'message': f'Service {action} successfully'}
    except subprocess.CalledProcessError as e:
        return {'status': 'error', 'message': f'Failed to {action} service: {str(e)}'}

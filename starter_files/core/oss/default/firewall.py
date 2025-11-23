from starter_files.core.base_module import BaseModule
import subprocess
import re
from typing import Dict, List, Tuple, Any
from starter_files.core.utils.globalVars_utils import set_global, get_global

class FirewallModule(BaseModule):

    @staticmethod
    def check() -> bool:
        """Проверяет доступность фаервол-утилит в системе"""
        return any([
            FirewallModule._check_tool('ufw'),
            FirewallModule._check_tool('firewall-cmd'),
            FirewallModule._check_tool('iptables'),
            FirewallModule._check_tool('nft')
        ])

    @staticmethod
    def _check_tool(tool_name: str) -> bool:
        """Проверяет наличие утилиты в системе"""
        try:
            subprocess.run(
                [tool_name, '--version'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    @staticmethod
    def detect_active_firewall() -> str:
        """Определяет активный фаервол в системе"""
        tools_priority = [
            ('ufw', 'ufw status | grep -q "Status: active"'),
            ('firewalld', 'firewall-cmd --state 2>/dev/null | grep -q "running"'),
            ('iptables', 'iptables -L -n 2>/dev/null | grep -q -v "Chain INPUT (policy ACCEPT)"'),
            ('nftables', 'nft list ruleset 2>/dev/null | grep -q "counter"')
        ]
        
        for tool, check_cmd in tools_priority:
            if FirewallModule._check_tool(tool) and subprocess.run(
                check_cmd, shell=True, check=False
            ).returncode == 0:
                return tool
        return "unknown"

    @staticmethod
    def get_open_ports() -> List[Dict[str, str]]:
        """Возвращает список открытых портов в формате:
        [{'port': '80', 'protocol': 'tcp', 'service': 'http'}, ...]
        """
        firewall_type = FirewallModule.detect_active_firewall()
        handler = {
            'ufw': FirewallModule._get_ufw_ports,
            'firewalld': FirewallModule._get_firewalld_ports,
            'iptables': FirewallModule._get_iptables_ports,
            'nftables': FirewallModule._get_nftables_ports
        }.get(firewall_type, FirewallModule._get_generic_ports)
        
        return handler()

    @staticmethod
    def _parse_port(port_spec: str) -> Tuple[str, str]:
        """Разбирает строку порта на номер и протокол"""
        if '/' in port_spec:
            port, protocol = port_spec.split('/')
        else:
            port = port_spec
            protocol = 'tcp'
        return port, protocol

    @staticmethod
    def _get_ufw_ports() -> List[Dict[str, str]]:
        """Получает открытые порты для ufw"""
        try:
            result = subprocess.run(
                ['ufw', 'status', 'verbose'],
                capture_output=True,
                text=True,
                check=True
            )
            
            ports = []
            for line in result.stdout.split('\n'):
                if 'ALLOW' in line and 'Anywhere' in line:
                    parts = line.split()
                    port_spec = parts[0]
                    port, protocol = FirewallModule._parse_port(port_spec)
                    ports.append({
                        'port': port,
                        'protocol': protocol,
                        'service': 'N/A'
                    })
            return ports
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def _get_firewalld_ports() -> List[Dict[str, str]]:
        """Получает открытые порты для firewalld"""
        try:
            result = subprocess.run(
                ['firewall-cmd', '--list-ports'],
                capture_output=True,
                text=True,
                check=True
            )
            
            ports = []
            for port_spec in result.stdout.split():
                port, protocol = FirewallModule._parse_port(port_spec)
                ports.append({
                    'port': port,
                    'protocol': protocol,
                    'service': 'N/A'
                })
            return ports
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def _get_iptables_ports() -> List[Dict[str, str]]:
        """Получает открытые порты через iptables с улучшенным парсингом"""
        try:
            # Получаем политики цепочек
            policies = FirewallModule._get_iptables_policies()
            input_policy = policies.get('INPUT', 'DROP')
            
            # Если политика INPUT - ACCEPT, все порты открыты
            if input_policy == 'ACCEPT':
                return [{
                    'port': 'ALL',
                    'protocol': 'ALL',
                    'service': 'Все порты разрешены (политика ACCEPT)',
                    'policy': 'ACCEPT'
                }]

            # Анализируем правила
            result = subprocess.run(
                ['iptables', '-L', 'INPUT', '-n', '--line-numbers', '-v'],
                capture_output=True,
                text=True,
                check=True
            )
            
            ports = []
            # Регулярное выражение для поиска разрешающих правил
            accept_pattern = re.compile(
                r'ACCEPT\s+(tcp|udp)\s+--\s+\S+\s+\S+\s+(?:tcp|udp) dpt:(\d+)'
            )
            
            # Регулярное выражение для поиска разрешающих правил по интерфейсу
            iface_pattern = re.compile(
                r'ACCEPT\s+(tcp|udp)\s+--\s+\S+\s+\S+\s+(?:tcp|udp) dpt:(\d+)\s+/\*\s+([\w-]+)\s+\*/'
            )
            
            for line in result.stdout.split('\n'):
                # Проверяем на разрешение всех портов
                if 'ACCEPT all -- 0.0.0.0/0 0.0.0.0/0' in line:
                    return [{
                        'port': 'ALL',
                        'protocol': 'ALL',
                        'service': 'Все порты разрешены',
                        'policy': 'RULE'
                    }]
                
                # Проверяем обычные правила для портов
                match = accept_pattern.search(line)
                if match:
                    protocol = match.group(1)
                    port = match.group(2)
                    ports.append({
                        'port': port,
                        'protocol': protocol,
                        'service': 'N/A',
                        'policy': 'RULE'
                    })
                    continue
                
                # Проверяем правила с указанием интерфейса
                iface_match = iface_pattern.search(line)
                if iface_match:
                    protocol = iface_match.group(1)
                    port = iface_match.group(2)
                    interface = iface_match.group(3)
                    ports.append({
                        'port': port,
                        'protocol': protocol,
                        'service': f'Разрешено на интерфейсе {interface}',
                        'policy': 'RULE'
                    })
            
            return ports
            
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def _get_nftables_ports() -> List[Dict[str, str]]:
        """Получает открытые порты через nftables"""
        try:
            result = subprocess.run(
                ['nft', 'list', 'ruleset'],
                capture_output=True,
                text=True,
                check=True
            )
            
            ports = []
            # Регулярное выражение для поиска правил accept
            pattern = re.compile(
                r'ip\s+(?:saddr|daddr)\s+\.\.\.\s+tcp\s+dport\s+(\d+)\s+accept'
            )
            
            for line in result.stdout.split('\n'):
                match = pattern.search(line)
                if match:
                    ports.append({
                        'port': match.group(1),
                        'protocol': 'tcp',
                        'service': 'N/A'
                    })
            return ports
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def _get_generic_ports() -> List[Dict[str, str]]:
        """Улучшенный метод для определения слушающих портов"""
        try:
            # Определяем доступную утилиту
            tools = ['ss', 'netstat']
            cmd = None
            for tool in tools:
                if FirewallModule._check_tool(tool):
                    cmd = [tool, '-tuln'] if tool == 'ss' else [tool, '-tuln']
                    break
            
            if not cmd:
                return []
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            ports = []
            for line in result.stdout.split('\n')[1:]:
                if not line.strip():
                    continue
                    
                parts = line.split()
                if not parts:
                    continue
                
                # Обработка вывода ss
                if cmd[0] == 'ss':
                    if len(parts) < 5 or 'LISTEN' not in parts[1]:
                        continue
                    local_address = parts[4]
                    protocol = parts[0]
                
                # Обработка вывода netstat
                else:
                    if len(parts) < 6 or 'LISTEN' not in parts[-1]:
                        continue
                    local_address = parts[3]
                    protocol = parts[0]
                
                # Парсим адрес и порт
                if ']:' in local_address:  # IPv6
                    port = local_address.split(']:')[-1]
                elif ':' in local_address:  # IPv4
                    port = local_address.split(':')[-1]
                else:
                    continue
                
                # Определяем состояние
                state = 'LISTEN'
                if cmd[0] == 'ss' and len(parts) > 1:
                    state = parts[1]
                
                ports.append({
                    'port': port,
                    'protocol': protocol.upper(),
                    'service': 'N/A',
                    'state': state
                })
            
            return ports
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    @staticmethod
    def _run_privileged_command(cmd: List[str]) -> bool:
        """Выполняет команду с привилегиями (sudo при необходимости)"""
        use_sudo = get_global('use_sudo')
        full_cmd = ['sudo'] + cmd if use_sudo else cmd
        
        try:
            subprocess.run(
                full_cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def open_port(port: int, protocol: str = 'tcp') -> bool:
        """Открывает порт в фаерволе"""
        firewall_type = FirewallModule.detect_active_firewall()
        
        handlers = {
            'ufw': ['ufw', 'allow', f'{port}/{protocol}'],
            'firewalld': [
                'firewall-cmd', '--add-port', f'{port}/{protocol}', '--permanent'
            ],
            'iptables': [
                'iptables', '-A', 'INPUT', '-p', protocol, 
                '--dport', str(port), '-j', 'ACCEPT'
            ],
            'nftables': [
                'nft', 'add', 'rule', 'inet', 'filter', 'input', 
                f'{protocol} dport {port} accept'
            ]
        }
        
        if firewall_type in handlers:
            return FirewallModule._run_privileged_command(handlers[firewall_type])
        
        return False

    @staticmethod
    def close_port(port: int, protocol: str = 'tcp') -> bool:
        """Закрывает порт в фаерволе"""
        firewall_type = FirewallModule.detect_active_firewall()
        
        handlers = {
            'ufw': ['ufw', 'delete', 'allow', f'{port}/{protocol}'],
            'firewalld': [
                'firewall-cmd', '--remove-port', f'{port}/{protocol}', '--permanent'
            ],
            'iptables': [
                'iptables', '-D', 'INPUT', '-p', protocol, 
                '--dport', str(port), '-j', 'ACCEPT'
            ],
            'nftables': [
                'nft', 'delete', 'rule', 'inet', 'filter', 'input', 
                f'{protocol} dport {port} accept'
            ]
        }
        
        if firewall_type in handlers:
            return FirewallModule._run_privileged_command(handlers[firewall_type])
        
        return False

    @staticmethod
    def collect_firewall_info() -> Dict[str, Any]:
        """Собирает расширенную информацию о фаерволе и портах"""
        active_firewall = FirewallModule.detect_active_firewall()
        open_ports = FirewallModule.get_open_ports()
        listening_ports = FirewallModule._get_generic_ports()
        
        # Проверяем, открыты ли все порты
        all_ports_open = False
        if open_ports and open_ports[0].get('port') == 'ALL':
            all_ports_open = True
        
        return {
            'active_firewall': active_firewall,
            'open_ports': open_ports,
            'listening_ports': listening_ports,
            'is_available': active_firewall != "unknown",
            'all_ports_open': all_ports_open
        }

    @staticmethod
    def _get_iptables_policies() -> Dict[str, str]:
        """Возвращает политики цепочек для iptables"""
        policies = {}
        try:
            result = subprocess.run(
                ['iptables', '-L', '-n'],
                capture_output=True,
                text=True,
                check=True
            )
            
            current_chain = None
            for line in result.stdout.split('\n'):
                chain_match = re.match(r'^Chain (\w+) \(policy (\w+)\)', line)
                if chain_match:
                    current_chain = chain_match.group(1)
                    policies[current_chain] = chain_match.group(2)
            return policies
        except subprocess.CalledProcessError:
            return {}

# Клеймение fingerprint для уже установленных серверов.
# Запускать при ОСТАНОВЛЕННОМ стартере (прямая правка реестра).
import json
import sys
from pathlib import Path

sys.path.insert(0, r'C:\control\starter')

from files.web.sections.servers import _ensure_fingerprint

REG = r'C:\ProgramData\starter-registry.json'

with open(REG, encoding='utf-8') as f:
    reg = json.load(f)

changed = False
for p in reg.get('projects', []):
    docker = Path(p['path']) / 'docker'
    env = docker / '.env'
    if env.exists():
        fp = _ensure_fingerprint(docker)
        if p.get('fingerprint') != fp:
            p['fingerprint'] = fp
            changed = True
        print(f"{p['path']} -> {fp}")
    else:
        print(f"{p['path']}: нет docker/.env — пропуск")

if changed:
    with open(REG, 'w', encoding='utf-8') as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    print('Реестр обновлён')
else:
    print('Изменений не было')

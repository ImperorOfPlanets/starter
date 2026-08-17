from flask import render_template, jsonify
from files.core.utils.loader_utils import get
from files.core.utils.log_utils import LogManager

logger = LogManager.get_logger()

def t(key: str, **kwargs) -> str:
    i18n = get('i18n')
    if i18n and hasattr(i18n, 'translate'):
        return i18n.translate(key, **kwargs)
    return key

this_section_in_control_panel = True
section_icon = "bi-git"
section_name = "Git"
section_order = 4
section_group = "software"
section_group_name = "Software"
section_group_icon = "bi-box-seam"


def index(data, session):
    git_installed = get('git', 'check_git_installed') or False
    git_auth = get('git', 'check_git_authentication') or 'N/A'
    return render_template(
        'sections/git/index.html',
        git_installed=git_installed,
        git_auth=git_auth,
        t=t
    )


def install_git_action(data, session):
    import uuid
    import threading
    from pathlib import Path
    from files.core.utils.globalVars_utils import get_global

    install_logs_dir = get_global('path_log_install')
    if install_logs_dir:
        install_logs_dir.mkdir(parents=True, exist_ok=True)

    install_id = str(uuid.uuid4())
    log_file_path = install_logs_dir / f"install_git_{install_id}.log"

    def run_installation():
        try:
            result = get('git', 'install_git', log_file_path=str(log_file_path))
            if result and result.get('status') == 'error':
                raise Exception(result.get('message', 'Unknown error'))
        except Exception as e:
            with open(log_file_path, 'a') as f:
                f.write(f"\nFATAL ERROR: {str(e)}\n")
                f.write("INSTALL FINISH!\n")
            logger.error(f"Git installation failed: {str(e)}")

    thread = threading.Thread(target=run_installation)
    thread.daemon = True
    thread.start()

    return jsonify({
        'status': 'started',
        'message': 'Git installation started',
        'install_id': install_id
    })


def get_install_logs(data, session):
    from pathlib import Path
    install_id = data.get('install_id')
    if not install_id:
        return jsonify({'status': 'error', 'message': 'Install ID required', 'logs': '', 'completed': False, 'installed': False})

    from files.core.utils.globalVars_utils import get_global
    install_logs_dir = get_global('path_log_install')
    log_file_path = install_logs_dir / f"install_git_{install_id}.log"

    if not log_file_path.exists():
        return jsonify({'status': 'error', 'message': 'Log not found', 'logs': '', 'completed': False, 'installed': False})

    try:
        with open(log_file_path, 'r') as f:
            logs = f.read()
        completed = "INSTALL FINISH!" in logs
        installed = completed and "ERROR" not in logs.upper() and "FATAL ERROR" not in logs.upper()
        return jsonify({'status': 'success', 'logs': logs, 'completed': completed, 'installed': installed})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'logs': '', 'completed': False, 'installed': False})

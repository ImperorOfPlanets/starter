import re
path = r'C:\control\starter\files\web\sections\servers.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the block to replace
start_marker = '        if repo_url and repo_credentials and repo_auth_type:\n'
end_marker = '            result = fetch_result\n        else:\n            result = subprocess.run(\n'

start = content.find(start_marker)
if start < 0:
    print("START NOT FOUND")
    exit(1)

# Find the else block end
idx = content.find('else:\n            result = subprocess.run(\n', start)
end = content.find('\n', idx + len('else:\n            result = subprocess.run(\n')) + 1
end = content.find('\n', end + 1) + 1

old_block = content[start:end]
print(f"Found block: {len(old_block)} chars")

new_block = '''        if repo_url and repo_credentials and repo_auth_type:
            from files.core.software.default.git_service import GitService
            auth_url = GitService.get_auth_url(repo_url, repo_credentials, repo_auth_type)
            logger.info(f"Update {project_type}: fetching with token, branch={repo_branch}")

            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_ASKPASS'] = 'echo'

            # Temporarily add token to .git-credentials for GCM
            home = os.path.expanduser('~')
            creds_path = os.path.join(home, '.git-credentials')
            old_creds = b''
            if os.path.exists(creds_path):
                with open(creds_path, 'rb') as f:
                    old_creds = f.read()
            with open(creds_path, 'ab') as f:
                f.write((auth_url + '\\n').encode())

            try:
                fetch_result = subprocess.run(
                    ['git', 'fetch', 'origin', f'{repo_branch}:refs/remotes/origin/{repo_branch}'],
                    cwd=str(git_dir), capture_output=True, text=True, timeout=30, env=env
                )
                logger.info(f"Update {project_type}: fetch exit={fetch_result.returncode}, stderr={fetch_result.stderr[:400]}")
            finally:
                with open(creds_path, 'wb') as f:
                    f.write(old_creds)

            if fetch_result.returncode == 0:
                result = subprocess.run(
                    ['git', 'merge', f'origin/{repo_branch}'],
                    cwd=str(git_dir), capture_output=True, text=True, timeout=30, env=env
                )
                logger.info(f"Update {project_type}: merge exit={result.returncode}, stdout={result.stdout[:200]}")
            else:
                result = fetch_result
        else:
            result = subprocess.run(
                ['git', 'pull'],
                cwd=str(git_dir), capture_output=True, text=True, timeout=30, env=env
            )
'''

content = content[:start] + new_block + content[end:]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE - file updated")

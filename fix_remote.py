import re

path = '/opt/starter/files/core/software/default/oauth.py'
with open(path, 'r') as f:
    content = f.read()

content = content.replace("host = 'localhost'", "host = OauthModule._detect_external_ip()")

with open(path, 'w') as f:
    f.write(content)

print("Fixed!")

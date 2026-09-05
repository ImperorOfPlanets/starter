# ====================== Ubuntu/Debian Family ======================

# Ubuntu 24.04 (Noble)
[ubuntu,24.04,python]="python3.12"
[ubuntu,24.04,pip]="python3-pip"
[ubuntu,24.04,python-dev]="python3.12-dev"
[ubuntu,24.04,python-venv]="python3.12-venv"
[ubuntu,24.04,unzip]="unzip"
[ubuntu,24.04,pre_install]="export DEBIAN_FRONTEND=noninteractive; apt-get update -y"
[ubuntu,24.04,install]="apt-get install -y --no-install-recommends"

# Ubuntu 22.04 (Jammy)
[ubuntu,22.04,python]="python3.10"
[ubuntu,22.04,pip]="python3-pip"
[ubuntu,22.04,python-dev]="python3.10-dev"
[ubuntu,22.04,python-venv]="python3.10-venv"
[ubuntu,22.04,unzip]="unzip"
[ubuntu,22.04,pre_install]="export DEBIAN_FRONTEND=noninteractive; apt-get update -y"
[ubuntu,22.04,install]="apt-get install -y --no-install-recommends"

# Ubuntu по умолчанию
[ubuntu,default,python]="python3"
[ubuntu,default,pip]="python3-pip"
[ubuntu,default,python-dev]="python3-dev"
[ubuntu,default,python-venv]="python3-venv"
[ubuntu,default,unzip]="unzip"
[ubuntu,default,pre_install]="export DEBIAN_FRONTEND=noninteractive; apt-get update -y"
[ubuntu,default,install]="apt-get install -y --no-install-recommends"

# Debian 12 (Bookworm)
[debian,12,python]="python3.11"
[debian,12,pip]="python3-pip"
[debian,12,python-dev]="python3-dev"
[debian,12,python-venv]=" "
[debian,12,unzip]="unzip"
[debian,12,pre_install]="apt-get update -y"
[debian,12,install]="apt-get install -y --no-install-recommends"

# Debian 11 (Bullseye)
[debian,11,python]="python3.9"
[debian,11,pip]="python3-pip"
[debian,11,python-dev]="python3-dev"
[debian,11,python-venv]="python3-venv"
[debian,11,unzip]="unzip"
[debian,11,pre_install]="apt-get update -y"
[debian,11,install]="apt-get install -y --no-install-recommends"

# Debian по умолчанию
[debian,default,python]="python3"
[debian,default,pip]="python3-pip"
[debian,default,python-dev]="python3-dev"
[debian,default,python-venv]="python3-venv"
[debian,default,unzip]="unzip"
[debian,default,pre_install]="apt-get update -y"
[debian,default,install]="apt-get install -y --no-install-recommends"

# ====================== RHEL Family ======================

# AlmaLinux 9.x
[almalinux,9,python]="python3"
[almalinux,9,pip]="python3-pip"
[almalinux,9,python-dev]=" "
[almalinux,9,python-venv]=" "
[almalinux,9,unzip]="unzip"
[almalinux,9,pre_install]="dnf update -y"
[almalinux,9,install]="dnf install -y"

# AlmaLinux 8.x
[almalinux,8,python]="python38"
[almalinux,8,pip]="python38-pip"
[almalinux,8,python-dev]="python38-devel"
[almalinux,8,python-venv]="python3-virtualenv"
[almalinux,8,unzip]="unzip"
[almalinux,8,pre_install]="dnf check-update || true; dnf install -y epel-release; dnf module reset -y python38; dnf module enable -y python38; dnf install -y platform-python-pip platform-python-devel"
[almalinux,8,install]="dnf install -y"

# Rocky Linux 9.x
[rocky,9,python]="python3.11"
[rocky,9,pip]="python3.11-pip"
[rocky,9,python-dev]="python3.11-devel"
[rocky,9,python-venv]="python3.11"
[rocky,9,unzip]="unzip"
[rocky,9,pre_install]="dnf update -y"
[rocky,9,install]="dnf install -y"

# Rocky Linux 8.x
[rocky,8,python]="python38"
[rocky,8,pip]="python38-pip"
[rocky,8,python-dev]="python38-devel"
[rocky,8,python-venv]=""
[rocky,8,unzip]="unzip"
[rocky,8,pre_install]="dnf install -y epel-release; dnf module reset -y python38; dnf module enable -y python38"
[rocky,8,install]="dnf install -y"

# CentOS 8
[centos,8,python]="python38"
[centos,8,pip]="python38-pip"
[centos,8,python-dev]="python38-devel"
[centos,8,python-venv]=""
[centos,8,unzip]="unzip"
[centos,8,pre_install]="dnf install -y epel-release; dnf module reset -y python38; dnf module enable -y python38"
[centos,8,install]="dnf install -y"

# Fedora 38+
[fedora,38,python]="python3.11"
[fedora,38,pip]="python3-pip"
[fedora,38,python-dev]="python3-devel"
[fedora,38,python-venv]="python3-virtualenv"
[fedora,38,unzip]="unzip"
[fedora,38,pre_install]="dnf update -y"
[fedora,38,install]="dnf install -y"

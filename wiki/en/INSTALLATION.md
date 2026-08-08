# Installation

Target platforms: Debian 12/13, Ubuntu Server 22.04/24.04 LTS and 64-bit Raspberry Pi OS based on Debian.

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y git curl ca-certificates python3 python3-pip python3-venv bluetooth bluez unattended-upgrades apt-listchanges

git clone https://github.com/jygnw29kms-bit/135er_GrowControl.git
cd 135er_GrowControl
sudo ./install/install.sh
```

Keep DF100M writes and cloud remote commands disabled until explicitly required and validated.

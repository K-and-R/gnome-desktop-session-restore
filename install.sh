#!/bin/bash

# This script (`install.sh`) is intended to install the software packages
# required for this tool to function as well as an example config file, if one
# doesn't already exist, and finally the session resotre script itself.

# Sudo
if [ !`sudo -n true 2>/dev/null` ]; then
  echo "Elevated privileges needed to complete setup and configuration. Please provide your password to sudo:"
  sudo echo
fi

# Install `curl`, `python` and `wmctrl`
sudo apt install -y curl python wmctrl

# Add a sample config file
if [ ! -e ~/.gnome-desktop-session.json ]; then
  curl -s https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/session.json.example -o ~/.gnome-desktop-session.json
fi

# Install the script
sudo mkdir -p /opt/K-and-R/gnome-desktop-session-restore/
sudo curl -s https://raw.githubusercontent.com/K-and-R/gnome-desktop-session-restore/v0.1.0/restore-gnome-desktop-session.py -o /opt/K-and-R/gnome-desktop-session-restore/restore-gnome-desktop-session.py
sudo chmod +x /opt/K-and-R/gnome-desktop-session-restore/restore-gnome-desktop-session.py

# Create the symlinks
if [ ! -e /usr/local/bin/restore-gnome-desktop-session.py ]; then
  sudo ln -s /opt/K-and-R/gnome-desktop-session-restore/restore-gnome-desktop-session.py /usr/local/bin/restore-gnome-desktop-session.py
elif [ -L /usr/local/bin/restore-gnome-desktop-session.py ];
  sudo rm /usr/local/bin/restore-gnome-desktop-session.py
  sudo ln -s /opt/K-and-R/gnome-desktop-session-restore/restore-gnome-desktop-session.py /usr/local/bin/restore-gnome-desktop-session.py
fi

if [ ! -e /usr/local/bin/restore-gnome-desktop-session ]; then
  sudo ln -s restore-gnome-desktop-session.py /usr/local/bin/restore-gnome-desktop-session
elif [ -L /usr/local/bin/restore-gnome-desktop-session ];
  sudo rm /usr/local/bin/restore-gnome-desktop-session
  sudo ln -s restore-gnome-desktop-session.py /usr/local/bin/restore-gnome-desktop-session
fi


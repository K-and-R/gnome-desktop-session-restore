#!/bin/bash

# This script (`uninstall.sh`) is intended to remove the files installed by the
# installation script (`install.sh`).

# Sudo
if [ !`sudo -n true 2>/dev/null` ]; then
  echo "Elevated privileges needed to complete uninstallation. Please provide your password to sudo:"
  sudo echo
fi

[ -L /usr/local/bin/restore-gnome-desktop-session ] && sudo rm -f /usr/local/bin/restore-gnome-desktop-session
[ -L /usr/local/bin/restore-gnome-desktop-session.py ] && sudo rm -f /usr/local/bin/restore-gnome-desktop-session.py
[ -d /opt/K-and-R/gnome-desktop-session-restore ] && sudo rm -rf /opt/K-and-R/gnome-desktop-session-restore
[ -e ~/.gnome-desktop-session.json ] && rm -f ~/.gnome-desktop-session.json

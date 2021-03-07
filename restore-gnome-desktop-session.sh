#!/bin/bash
#
# Run GNOME desktop sessino restore

python3 -u restore-gnome-desktop-session.py -vvv >> /home/karl/log/session-restore.log 2>&1

[ '0' == "${?}" ] || echo 'restore-gnome-desktop-session.py exited with a non-zero exit code. Check the log file for more details: /home/karl/log/session-restore.log'

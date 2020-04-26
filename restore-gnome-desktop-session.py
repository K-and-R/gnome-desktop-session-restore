#!/usr/bin/python
#
# `restore-gnome-desktop-session.py`
#
# This script is intended to restore the virtual desktop(s) as saved in the
# session configuration file (default: `~/.gnome-desktop-session.json`).
#
# Author: Karl Wilbur <karl@kandrsoftware.com>
#
#

import json as simplejson;
import argparse, time, subprocess, sys;

try:
    from subprocess import DEVNULL # py3k
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

__args = []
__session_data = ''
__displays = []
__workspaces = []

def args():
  global __args
  if not __args:
    __args = parse_invocation_args()
  return __args

def center_on_display(width, height, display):
  if args().verbose > 0:
    print('center_on_display()')
  d_left = int(display.get('left'))
  d_right = int(display.get('right'))
  left = (abs(d_right - d_left - int(width)) / 2) + d_left
  d_top = int(display.get('top'))
  d_bottom = int(display.get('bottom'))
  if args().verbose > 2:
    print('display dimensions (left, top, right, bottom): '+str(d_left)+','+str(d_top)+','+str(d_right)+','+str(d_bottom))
  top = (abs(d_bottom - d_top - int(height)) / 2) + d_top
  if args().verbose > 2:
    print('window dimensions (width, height): '+str(width)+','+str(height))
  if args().verbose > 2:
    print('window position (top, left): '+str(top)+','+str(left))
  return [top, left]

def displays():
  global __displays
  if not __displays:
    __displays = session_data()['displays']
  return __displays

def execute_process(cmd):
  if args().verbose > 0:
    print('execute_process(' + ' '.join(cmd) + ')')
  # return subprocess.Popen(cmd)
  return subprocess.Popen(cmd, stdout=DEVNULL, stderr=subprocess.STDOUT)

def find_new_windows(current_windows):
  if args().verbose > 1:
    print('find_new_windows()')
  new_windows = get_current_window_list()
  return list_diff(new_windows, current_windows)

def get_current_window_list():
  if args().verbose > 1:
    print('get_current_window_list()')
  proc_output = get_process_output(['wmctrl', '-l'])
  current_windows = []
  for w in proc_output.splitlines():
    window_id = str(w.split()[0])
    if args().verbose > 3:
      print('window: ' + window_id)
    current_windows.append(window_id)
  return current_windows

def get_display_by_position(position):
  for display in displays():
    if display.get('position') == position:
      return display

def get_process_output(cmd):
  if args().verbose > 0:
    print('get_process_output(' + ' '.join(cmd) + ')')
  try:
    return subprocess.check_output(cmd).decode('utf-8').strip()
  except (subprocess.CalledProcessError, TypeError):
    pass

def get_window_geometry(window_id, app):
  if args().verbose > 1:
    print('get_window_geometry()')
  # window = get_process_output(['wmctrl', '-lG', '|', 'grep', window_id])
  proc_output = get_process_output(['wmctrl', '-lG'])
  for line in proc_output.splitlines():
    if line.find(window_id) == 0:
      window = line
  if args().verbose > 2:
    print('Raw response: '+window)
  window = window.split()
  if args().verbose > 2:
    print('Windows gemometry (left,top,width,height): '+window[2]+','+window[3]+','+window[4]+','+window[5])
  gravity = 0
  left    = int(window[2])
  top     = int(window[3])
  width   = int(window[4])
  height  = int(window[5])

  if app.get('size'):
    width, height = app.get('size').split('x')
  if app.get('position'):
    left, top = app.get('position').split('x')
  if app.get('display'):
    if app.get('position'):
      # If we have a display and position, set that position
      # relative to that display
      left = int(left) + int(display.get('left'))
      top  = int(top)  + int(display.get('top'))
    else:
      # If no position, center on the display
      top, left = center_on_display(width, height, get_display_by_position(app.get('display')))
  if args().verbose > 1:
    print('positioning window  (left,top,width,height): '+str(left)+','+str(top)+','+str(width)+','+str(height))
  return [str(gravity), str(left), str(top), str(width), str(height)]

def list_diff(first, second):
  global args
  if args().verbose > 1:
    print('list_diff()')
  second = set(second)
  return [item for item in first if item not in second]

def parse_invocation_args():
  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument(
    '--version',
    action='version',
    version='%(prog)s 0.1.0'
    )
  parser.add_argument(
    '--verbose',
    '-v',
    help='increase message verbosity; stackable',
    action='count'
    )
  parser.add_argument(
    '-s',
    '--session-file',
    action='store',
    nargs='?',
    type=argparse.FileType('r'),
    help='the session file from which to restore (default: session.json)',
    default='~/.gnome-desktop-session.json'
    )
  return parser.parse_args()

def session_data():
  global __session_data
  if not __session_data:
    __session_data = simplejson.load(args().session_file)
  return __session_data

def set_up_workspace(workspace, workspace_index):
  if args().verbose > 0:
    print('Workspace Name: ' + workspace['name'])
    print('Workspace Index: {}'.format(workspace_index))
  apps = workspace.get('apps')
  if apps:
    for app in apps:
      cmd = app.get('command')
      cmd_args = app.get('args', [])
      app_command = cmd
      app_command = app_command + ' ' + ' '.join(cmd_args)
      if args().verbose > 0:
        print('App Command: ' + app_command)
      current_windows = get_current_window_list()
      execute_process( [cmd] + cmd_args )
      new_windows = wait_for_new_windows(current_windows,app)
      if len(new_windows) > 1:
        print('Multiple windows found for command.')
        print('    command: ' + app_command)
        print('    windows: {}'.format(new_windows))
      for w in new_windows:
        if args().verbose > 1:
          print('Window ID: ' + w)
        # Set attributes
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove','add')[app.get('sticky', False)] + ',sticky'])
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove','add')[app.get('maximized', False)] + ',maximized_vert,maximized_horz'])
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove','add')[app.get('fullscreen', False)] + ',fullscreen'])
        # Set position
        if app.get('position') or app.get('size') or app.get('display'):
          execute_process(['wmctrl', '-i', '-r', w, '-e', ','.join(get_window_geometry(w,app))])
        # Move to correct workspace
        execute_process(['wmctrl', '-i', '-r', w, '-t', str(workspace_index)])
      if args().verbose > 1:
        print('')
  if args().verbose > 0:
    print('')

def wait_for_new_windows(current_windows,app):
  if args().verbose > 1:
    print('wait_for_new_windows()')
    print('Current windows: {}'.format(current_windows))
  new_windows = []
  sleep_cycles = 0
  if app.get('run_in_background'):
    if args().verbose > 1:
    	print('App runs in background, no new windows expected.')
    return new_windows # No new windows for this app
  time.sleep(app.get('startup_delay',2)) # wait for window to open
  new_windows = find_new_windows(current_windows)
  while len(new_windows) == 0:
    sleep_cycles += 1
    if sleep_cycles >= 5:
      print('Max sleep cycles reaching waiting for new windows.')
      print('Current windows: {}'.format(current_windows))
      print('New windows: {}'.format(new_windows))
      sys.exit()
    if args().verbose > 1:
      print('starting another sleep cycle, waiting for new windows')
    time.sleep(2)
    new_windows = find_new_windows(current_windows)
  return new_windows

def workspaces():
  global __workspaces
  if not __workspaces:
    __workspaces = session_data()['workspaces']
  return __workspaces

### MAIN

# Process each defined workspace
print('Loading session from '+args().session_file.name)
for workspace_index, workspace in enumerate(workspaces()):
  set_up_workspace(workspace, workspace_index)

# Switch back to the first workspace
subprocess.Popen(['wmctrl', '-s', '0'])

print('Done')

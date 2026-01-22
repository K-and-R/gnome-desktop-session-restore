#!/usr/bin/python
#
# `restore-gnome-desktop-session.py`
#
# This script is intended to restore the virtual desktop(s) as saved in the
# session configuration file (default: `~/.gnome-desktop-session.json`).
#
# Author: Karl Wilbur <karl@kandrsoftware.com>
#

import argparse
import fcntl
import json
import logging
import os
import shutil
import subprocess
import sys
import time

try:
  from subprocess import DEVNULL
except ImportError:
  DEVNULL = open(os.devnull, 'wb')

__args = []
__displays = []
__session_data = ''
__workspaces = []
__WAIT_CYCLE_SECONDS = 2

logger = logging.getLogger()

def acquire_lock():
  lock_file = open('/tmp/gnome-desktop-session.lock', 'w')
  try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return lock_file
  except IOError:
    logger.error('Another instance is running')
    logger.warning('Exiting')
    sys.exit(1)

def app_command_with_args(app):
  return app.get('command') + ' ' + ' '.join(app.get('args', []))

def args():
  global __args
  if not __args:
    __args = parse_invocation_args()
  return __args

def center_on_display(width, height, display):
  logger.info('center_on_display()')
  d_left = int(display.get('left'))
  d_right = int(display.get('right'))
  left = (abs(d_right - d_left - int(width)) / 2) + d_left
  d_top = int(display.get('top'))
  d_bottom = int(display.get('bottom'))
  if args().verbose > 2:
    logger.debug(f'display dimensions (left, top, right, bottom): {d_left},{d_top},{d_right},{d_bottom}')
  top = int(abs(d_bottom - d_top - int(height)) / 2) + d_top
  if args().verbose > 2:
    logger.debug(f'window dimensions (width, height): {width},{height}')
    logger.debug(f'window position (top, left): {top},{left}')
  return [top, left]

def check_dependencies():
  '''Check for required external tools, exit with error if missing.'''
  tools = ['wmctrl', 'xdotool']
  missing = [tool for tool in tools if shutil.which(tool) is None]
  if missing:
    logger.error(f'Error: Missing dependencies: {', '.join(missing)}')
    logger.error(f'Install them with: sudo apt install {' '.join(missing)}')
    logger.warning('Exiting')
    sys.exit(1)

def displays():
  global __displays
  if not __displays:
    __displays = session_data()['displays']
  return __displays

def execute_process(cmd):
  cmd_id = id(cmd)
  logger.info(f'execute_process({' '.join(cmd)}, id={cmd_id})')
  try:
    return subprocess.Popen(cmd, stdout=DEVNULL, stderr=subprocess.STDOUT)
  except FileNotFoundError:
    logger.critical(f'Command not found: {' '.join(cmd)}')
    logger.warning('Exiting')
    sys.exit(1)

def find_new_windows(current_windows):
  logger.debug('find_new_windows()')
  new_windows = get_current_window_list()
  return list_diff(new_windows, current_windows)

def get_current_window_list():
  logger.debug('get_current_window_list()')
  proc_output = get_process_output(['wmctrl', '-l'])
  current_windows = []
  for w in proc_output.splitlines():
    window_id = str(w.split()[0])
    if args().verbose > 3:
      logger.debug(f'window: {window_id}')
    current_windows.append(window_id)
  return current_windows

def get_display_by_position(position):
  for display in displays():
    if display.get('position') == position:
      return display

def get_process_output(cmd):
  logger.info(f'get_process_output({' '.join(cmd)})')
  try:
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').strip()
    if not output and args().verbose > 2:
      logger.debug(f'Command {' '.join(cmd)} returned empty output')
    return output
  except subprocess.CalledProcessError as e:
    if args().verbose > 1:
      logger.debug(f'Command {' '.join(cmd)} failed with exit code {e.returncode}: {e.output.decode('utf-8')}')
    return ''
  except TypeError:
    logger.error(f'TypeError in command {' '.join(cmd)}')
    return ''

def get_window_geometry(window_id, app):
  logger.debug(f'get_window_geometry() for window_id {window_id}')
  proc_output = get_process_output(['wmctrl', '-lG'])
  if args().verbose > 2:
    logger.debug(f'Raw proc_output: {proc_output}')
  window = None
  for line in proc_output.splitlines():
    if line.find(window_id) == 0:
      window = line
      break
  if not window:
    logger.warning(f'No geometry found for window {window_id}')
    return ['0', '0', '0', '800', '600']
  logger.debug(f'Process window: {window}')
  window = window.split()
  if args().verbose > 2:
    logger.debug(f'Windows geometry (left,top,width,height): {window[2]},{window[3]},{window[4]},{window[5]}')
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
    display = get_display_by_position(app.get('display'))
    if app.get('position'):
      # If we have a display and position, set that position
      # relative to that display
      left = int(left) + int(display.get('left'))
      top  = int(top)  + int(display.get('top'))
    else:
      # If no position, center on the display
      top, left = center_on_display(width, height, display)
  logger.debug(f'positioning window (left,top,width,height): {left},{top},{width},{height}')
  return [str(gravity), str(left), str(top), str(width), str(height)]

def list_diff(first, second):
  logger.debug('list_diff()')
  second = set(second)
  return [item for item in first if item not in second]

def parse_invocation_args():
  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument(
    '--version',
    action='version',
    version='%(prog)s 0.2.0'
  )
  parser.add_argument(
    '--verbose',
    '-v',
    help='increase message verbosity; stackable',
    action='count',
    default=0
  )
  parser.add_argument(
    '-s',
    '--session-file',
    action='store',
    nargs='?',
    type=argparse.FileType('r'),
    help='the session file from which to restore (default: session.json)',
    default=os.path.expanduser('~/.gnome-desktop-session.json')
  )
  parser.add_argument(
    '-w',
    '--max-wait',
    action='store',
    nargs='?',
    type=int,
    help='Max seconds to wait for a new window',
    default=60
  )
  return parser.parse_args()

def session_data():
  global __session_data
  if not __session_data:
    try:
      __session_data = json.load(args().session_file)
    except json.JSONDecodeError as e:
      logger.error(f'Error decoding JSON file {args().session_file.name}: {e}')
      logger.warning('Please check the file for invalid syntax')
      logger.warning('Exiting')
      sys.exit(1)
  return __session_data

def set_up_workspace(workspace, workspace_index):
  logger.info(f'Workspace Name: {workspace["name"]}')
  logger.info(f'Workspace Index: {workspace_index}')
  # Expand the number of workspaces
  execute_process(['wmctrl', '-n', str(workspace_index)])
  apps = workspace.get('apps')
  if apps:
    for app in apps:
      cmd = app.get('command')
      cmd_args = app.get('args', [])
      app_command = app_command_with_args(app)
      logger.info(f'App Command: {app_command}')
      current_windows = get_current_window_list()
      proc = execute_process([cmd] + cmd_args)
      new_windows = wait_for_new_windows(current_windows, app, proc)
      if len(new_windows) > 1:
        logger.info('Multiple windows found for command.')
        logger.info(f'    command: {app_command}')
        logger.info(f'    windows: {new_windows}')
      for w in new_windows:
        logger.debug(f'Window ID: {w}')
        # Set attributes
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove', 'add')[app.get('sticky', False)] + ',sticky'])
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove', 'add')[app.get('maximized', False)] + ',maximized_vert,maximized_horz'])
        execute_process(['wmctrl', '-i', '-r', w, '-b', ('remove', 'add')[app.get('fullscreen', False)] + ',fullscreen'])
        # Set position
        if app.get('position') or app.get('size') or app.get('display'):
          execute_process(['wmctrl', '-i', '-r', w, '-e', ','.join(get_window_geometry(w, app))])
        # Move to correct workspace
        execute_process(['wmctrl', '-i', '-r', w, '-t', str(workspace_index)])
      logger.debug('')
  logger.info('')

def set_workspace_names(names):
  if len(names) > 0:
    execute_process(['gsettings', 'set', 'org.gnome.desktop.wm.preferences', 'workspace-names', f'"[\'{"', '".join(names)}\']"'])

def wait_for_new_windows(current_windows, app, proc):
  '''
  Wait for new windows from an app, using PID to filter and stabilizing dynamically.

  Args:
      current_windows (list): Window IDs before launching the app.
      app (dict): App config with 'command', 'args', and optional 'run_in_background'.
      proc (Popen): Process object from execute_process.

  Returns:
      list: New window IDs associated with the app.
  '''
  if app.get('run_in_background'):
    logger.info('App runs in background, no windows expected')
    return []

  cmd = app.get('command')
  cmd_args = app.get('args', [])
  max_wait = args().max_wait  # Max timeout for slow apps
  pid = proc.pid
  poll_interval = 0.5  # Fast polling
  stable_time = 3  # Seconds of no new windows to consider stable

  logger.debug(f'Waiting for windows from PID {pid} ({cmd})')

  elapsed = 0
  last_count = 0
  matched_windows = set()
  stable_elapsed = 0

  while elapsed < max_wait:
    new_windows = get_current_window_list()
    new_ids = set(new_windows) - set(current_windows)
    xdotool_output = get_process_output(['xdotool', 'search', '--pid', str(pid)])
    if xdotool_output:
      pid_windows = set(xdotool_output.splitlines()) & new_ids
      if pid_windows:
        matched_windows.update(pid_windows)
        logger.debug(f'PID {pid} windows at {elapsed}s: {pid_windows}')
    elif args().verbose > 2:
      logger.debug(f'No xdotool output for PID {pid} at {elapsed}s')

    # Fallback to diff if no PID match (e.g., Snap wrapper or headless)
    if not matched_windows and new_ids:
      matched_windows.update(new_ids)
      logger.info(f'Fallback diff at {elapsed}s: {new_ids}')

    # Check stabilization
    current_count = len(matched_windows)
    if current_count > last_count:
      last_count = current_count
      # Reset if new windows appear
      stable_elapsed = 0
    else:
      stable_elapsed += poll_interval

    # Return if we have windows and they've stabilized
    if current_count > 0 and stable_elapsed >= stable_time:
      logger.debug(f'Stabilized after {elapsed}s with {current_count} windows: {matched_windows}')
      return list(matched_windows)

    # Check if process has exited (for headless apps), giving it one second to spawn
    if proc.poll() is not None and elapsed > 1:
      logger.debug(f'Process {pid} exited, returning {matched_windows}')
      return list(matched_windows)

    time.sleep(poll_interval)
    elapsed += poll_interval

  if matched_windows:
    logger.info(f'Max wait {max_wait}s reached, returning: {matched_windows}')
    return list(matched_windows)
  logger.warning(f'No windows for {cmd} (PID {pid}) after {max_wait} seconds')
  return []

def workspaces():
  global __workspaces
  if not __workspaces:
    __workspaces = session_data()['workspaces']
  return __workspaces

### MAIN

if __name__ == '__main__':
  ## Set up logging
  logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03dZ: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
  )
  logger = logging.getLogger()
  log_level = logging.WARNING
  if args().verbose > 1:
    log_level = logging.DEBUG
  elif args().verbose > 0:
    log_level = logging.INFO
  logger.setLevel(log_level)

  lock = acquire_lock()

  # Ensure that we have depandencies installed
  check_dependencies()

  # Process each defined workspace
  logger.info(f'Loading session from {args().session_file.name}')

  # Wait for any other starting processes to finish before processing the session
  time.sleep(10)
  workspace_index = 0
  workspace_names = []
  for _index, workspace in enumerate(workspaces()):
    if workspace.get('disabled'):
      continue
    set_up_workspace(workspace, workspace_index)
    workspace_names.append(workspace['name'])
    workspace_index += 1

  set_workspace_names(workspace_names)

  # Switch back to the first workspace
  subprocess.Popen(['wmctrl', '-s', '0'])

  logger.info('Done')

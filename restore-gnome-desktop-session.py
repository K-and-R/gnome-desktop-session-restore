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
import shlex
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
  args = []
  for arg in app.get('args', []):
    if not arg.startswith('-'):
      arg = shlex.quote(arg)
    args.append(arg)
  return app.get('command') + ' ' + ' '.join(args)

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
  #tools = ['wmctrl', 'xdotool']
  tools = ['wmctrl']
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
  exec_cmd = cmd
  command = cmd
  cmd_id = id(cmd)
  try:
    if type(cmd).__name__ == 'list':
      # an array was passed
      exec_cmd = cmd[0]
      command = ' '.join(cmd)
      logger.info(f'execute_process({command}, id={cmd_id})')
      return subprocess.Popen(cmd, stdout=DEVNULL, stderr=subprocess.STDOUT)
    else:
      # A string was passed
      logger.info(f'execute_process({cmd}), id={cmd_id})')
      return subprocess.Popen(cmd, shell=True, stdout=DEVNULL, stderr=subprocess.STDOUT)
  except FileNotFoundError:
    logger.critical(f'Command not found: {exec_cmd} (full command with args: {command})')
    logger.warning('Exiting')
    sys.exit(1)

def find_new_windows(current_window_ids):
  logger.debug('find_new_windows()')
  return list_diff(get_current_window_ids(), current_window_ids)

def get_current_window_ids():
  logger.debug('get_current_window_ids()')
  current_window_ids = []
  for w in get_windows_from_wmctrl():
    window_id = str(w.split()[0])
    if args().verbose > 3:
      logger.debug(f'window: {window_id}')
    current_window_ids.append(window_id)
  return current_window_ids

def get_display_by_position(position):
  for display in displays():
    if display.get('position') == position:
      return display

def get_process_output(cmd):
  if type(cmd).__name__ == 'list':
    # an array was passed
    command = {' '.join(cmd)}
  else:
    command = cmd
  logger.info(f'get_process_output({command})')
  try:
    output = subprocess.check_output({command}, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
    if not output and args().verbose > 2:
      logger.debug(f'Command {command} returned empty output')
    return output
  except subprocess.CalledProcessError as e:
    if args().verbose > 1:
      logger.debug(f'Command {command} failed with exit code {e.returncode}: {e.output.decode('utf-8')}')
    return False
  except TypeError:
    logger.error(f'TypeError in command {command}')
    return False

def get_window_from_wmctrl(window_id, additional_wmctrl_params=''):
  logger.debug(f'get_window_from_wmctrl() for window_id {window_id}')
  window = None
  for line in get_windows_from_wmctrl(additional_wmctrl_params):
    if line.find(window_id) == 0:
      window = line
      break
  logger.debug(f'Process window: {window}')
  return window

def get_windows_from_wmctrl(additional_wmctrl_params=''):
  logger.debug(f'get_windows_from_wmctrl()')
  proc_output = get_process_output(f'wmctrl -l {additional_wmctrl_params}')
  if args().verbose > 3:
    logger.debug(f'Raw proc_output: {proc_output}')
  return proc_output.splitlines()

def get_window_geometry(window_id, app):
  logger.debug(f'get_window_geometry() for window_id {window_id}')
  window = get_window_from_wmctrl(window_id, '-G')
  if not window:
    logger.warning(f'No geometry found for window {window_id}')
    return ['0', '0', '0', '800', '600']
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

def move_window_to_workspace(window_id, workspace_index):
  logger.debug(f'move_window_to_workspace() for window_id {window_id} and workspace_index {workspace_index}')
  available = get_process_output('gsettings get org.gnome.desktop.wm.preferences num-workspaces')
  if int(workspace_index) >= int(available):
    logger.warning(f'Requested index ({workspace_index}) exceeds available workspaces indexes ({int(available) - 1}).')
    set_dynamic_workspaces(workspace_index + 1)
  # Move window
  execute_process(f'wmctrl -i -r {window_id} -t {str(workspace_index)}')
  time.sleep(0.1)
  # Wait up to 2 seconds for changes in `wmctrl -l` to make sure window was actually moved
  max_attempts = 10
  for attempt in range(max_attempts):
    window_line = get_window_from_wmctrl(window_id)
    if not window_line:
      logger.warning(f'Window {window_id} disappeared during move check; assuming transient, skipping confirmation')
      return
    window = window_line.split()
    current_workspace = window[1]
    if current_workspace == str(workspace_index):
      logger.debug(f'Window {window_id} successfully moved to workspace {workspace_index}')
      return
    logger.debug(f'Waiting for move... attempt {attempt}/{max_attempts} (current={current_workspace}, wanted={workspace_index})')
    time.sleep(0.2)
  logger.error(f'Failed to confirm move of window {window_id} to workspace {workspace_index} after {max_attempts} attempts')

def parse_invocation_args():
  parser = argparse.ArgumentParser(
    description='Restore GNOME desktop session from saved configuration',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    add_help=True
  )
  parser.add_argument(
    '-V',
    '--version',
    action='version',
    version='%(prog)s 0.2.0'
  )
  parser.add_argument(
    '-v',
    '--verbose',
    help='increase message verbosity (repeatable for increased verbosity)',
    action='count',
    default=0
  )
  parser.add_argument(
    '-s',
    '--session-file',
    action='store',
    metavar='FILE_NAME',
    nargs='?',
    type=argparse.FileType('r'),
    help='the session file from which to restore (default: ~/.gnome-desktop-session.json)',
    default=os.path.expanduser('~/.gnome-desktop-session.json')
  )
  parser.add_argument(
    '-d',
    '--startup-delay',
    action='store',
    metavar='DELAY',
    nargs='?',
    type=int,
    help='Delay for starting to process workspaces',
    default=10
  )
  parser.add_argument(
    '-w',
    '--max-wait',
    action='store',
    metavar='SECONDS',
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

def set_dynamic_workspaces(num_workspaces):
  logger.info(f'Setting workspace count to {num_workspaces}')
  execute_process('gsettings set org.gnome.mutter dynamic-workspaces false')
  time.sleep(0.5) # Wait for Mutter to update
  execute_process(f'gsettings set org.gnome.desktop.wm.preferences num-workspaces {str(num_workspaces)}')
  max_attempts = 10
  for attempt in range(max_attempts):
    actual = get_process_output('gsettings get org.gnome.desktop.wm.preferences num-workspaces')
    actual = actual.strip("' \n")  # clean up quotes/whitespace
    if actual == str(num_workspaces):
      logger.debug(f'Workspace count confirmed: {num_workspaces}')
      return
    logger.debug(f'Workspace count check {attempt+1}/{max_attempts}: got {actual}, wanted {num_workspaces}')
    time.sleep(0.5)
  else:
    logger.error(f'Failed to set workspace count to {num_workspaces} after {max_attempts} checks (got {actual})')
    logger.warning('Exiting')
    sys.exit(1)

def set_up_workspace(workspace, workspace_index):
  logger.info(f'Workspace Name: {workspace["name"]}')
  logger.info(f'Workspace Index: {workspace_index}')
  apps = workspace.get('apps')
  if apps:
    for app in apps:
      cmd = app.get('command')
      cmd_args = app.get('args', [])
      app_command = app_command_with_args(app)
      logger.info(f'App Command: {app_command}')
      current_window_ids = get_current_window_ids()
      proc = execute_process([cmd] + cmd_args)
      if app.get('run_in_background'):
        logger.info('App runs in background, no windows expected')
        continue
      new_windows = [win_id for win_id in wait_for_new_windows(current_window_ids, app, proc) if get_window_from_wmctrl(win_id)]
      if not new_windows:
        logger.error('No windows found for command.')
        logger.info(f'    command: {app_command}')
        logger.warning('Exiting')
        sys.exit(1)
      elif len(new_windows) > 1:
        logger.info('Multiple windows found for command.')
        logger.info(f'    command: {app_command}')
        logger.info(f'    windows: {new_windows}')
      for win_id in new_windows:
        logger.debug(f'Window ID: {win_id}')
        # Set attributes
        execute_process(['wmctrl', '-i', '-r', win_id, '-b', ('remove', 'add')[app.get('sticky', False)] + ',sticky'])
        execute_process(['wmctrl', '-i', '-r', win_id, '-b', ('remove', 'add')[app.get('maximized', False)] + ',maximized_vert,maximized_horz'])
        execute_process(['wmctrl', '-i', '-r', win_id, '-b', ('remove', 'add')[app.get('fullscreen', False)] + ',fullscreen'])
        # Set position
        if app.get('position') or app.get('size') or app.get('display'):
          execute_process(f'wmctrl -i -r {win_id} -e {','.join(get_window_geometry(win_id, app))}')
        # Move to correct workspace
        move_window_to_workspace(win_id, workspace_index)
      logger.debug('')
  logger.info('')

def set_workspace_names(names):
  if len(names) > 0:
    # Create numbered names: 1-based index + " - " + original name
    numbered_names = [f'{i+1} - {name}' for i, name in enumerate(names)]
    # Join with single quotes and commas for gsettings array syntax
    names_str = "', '".join(numbered_names)
    # Build the full gsettings array string
    gsettings_value = f"['{names_str}']"
    execute_process(f'gsettings set org.gnome.desktop.wm.preferences workspace-names "{gsettings_value}"')

def wait_for_new_windows(current_window_ids, app, proc):
  if app.get('run_in_background'):
    logger.info('App runs in background, no windows expected')
    return []
  cmd = app.get('command')
  cmd_args = app.get('args', [])
  max_wait = args().max_wait  # Max timeout for slow apps
  pid = proc.pid
  poll_interval = 0.5  # Fast polling
  stable_time = app.get('stable_time', 2)  # Seconds of no new windows to consider stable
  delay = app.get('startup_delay')
  if delay:
    stable_time = delay
  logger.debug(f'Waiting for windows from PID {pid} ({cmd})')
  elapsed = 0
  last_count = 0
  matched_windows = set()
  stable_elapsed = 0
  while elapsed < max_wait:
    new_ids = set(get_current_window_ids()) - set(current_window_ids)
    if new_ids:
      matched_windows.update(new_ids)
      #logger.info(f'Fallback diff at {elapsed}s: {new_ids}')
      logger.info(f'New windows at {elapsed}s: {new_ids}')
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
    # Check if process has exited (for headless apps), giving it time to spawn
    if proc.poll() is not None and elapsed > max_wait:
      logger.debug(f'Process {pid} exited, returning {', '.join(list(matched_windows))}')
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
  set_dynamic_workspaces(len(workspaces()) + 2)
  set_workspace_names([workspace['name'] for workspace in workspaces()])
  # Wait for any other starting processes to finish before processing the session
  time.sleep(args().startup_delay)
  workspace_index = 0
  for _index, workspace in enumerate(workspaces()):
    logger.info(f'Processing workspace {str(workspace_index)}')
    # Switch back to the first workspace on each iteration
    execute_process('wmctrl -s 0')
    if workspace.get('disabled'):
      continue
    set_up_workspace(workspace, workspace_index)
    workspace_index += 1
  # Switch back to the first workspace
  execute_process('wmctrl -s 0')
  # Sometimes Gnome (well, Mutter) reset the workspace names. Set them again to be certain.
  set_workspace_names([workspace['name'] for workspace in workspaces()])
  logger.info('Done')


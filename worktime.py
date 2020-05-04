#!/usr/bin/python
import sys
import json
import csv
import os
import copy
import json
import argparse
from datetime import datetime
from datetime import timedelta
from dateutil import parser as date_parser
try:
  # Mac OS only
  import Quartz
except ImportError:
  # Windows
  import ctypes

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

class Config:
  def __init__(self):
    self.daily_work_minutes = 450
    self.daily_break_minutes = 30
    self.notifications = True
    self.date_format = '%Y-%m-%d'
    self.time_format = '%H:%M:%S'
    self.lock_break = False
    self.filename = '{}/work_hours.csv'.format(SCRIPT_PATH)

CONFIG_FILE = '{}/config.json'.format(SCRIPT_PATH)
CONFIG = Config()

START_OF_THE_DAY = '00:00:00'

# Indexes for CSV data
IDX_DATE = 0
IDX_START = 1
IDX_END = 2
IDX_OT = 3
IDX_TYPE = 4
IDX_BREAK = 5
IDX_WORKTIME = 6
IDX_STATUS = 7

# Parse command line arguments
def parse_args():
  parser = argparse.ArgumentParser(description='Work hour automator')

  parser.add_argument('-d', '--date', required=False, default=datetime.today(), type=lambda s: date_parser.parse(s),
      help='Date for manual commands, default: today')
  parser.add_argument('-f', '--flex', required=False, action='store_true',
      help='Add flex day for given date (-d or --date)')
  parser.add_argument('-s', '--start', nargs='?', const='now', type=lambda s: parse_time(s),
      help='Modify start time for given date (-d or --date). Default: now')
  parser.add_argument('-e', '--end', nargs='?', const='now', type=lambda s: parse_time(s),
      help='Modify end time for given date (-d or --date). Default: now')
  parser.add_argument('-ab', '--add-break', dest='addbreakmin', required=False, type=int,
      help='Add break time in minutes for given date (-d or --date)')
  parser.add_argument('-rb', '--remove-break', dest='removebreakmin', required=False, type=int,
      help='Remove break time in minutes from given date (-d or --date)')
  parser.add_argument('-wt', '--worktime', required=False, type=int,
      help='Set work time in minutes for given date (-d or --date)')
  parser.add_argument('-rc', '--recalculate', action='store_true',
      help='Recalculate work time in given file')
  parser.add_argument('--config', required=False, action='store_true',
      help='Configure the tool')
  parser.add_argument('filename', nargs='?', default=CONFIG.filename,
      help='File to save work hours to (default: {})'.format(CONFIG.filename))
  return parser.parse_args()

def write_configuration():
  s = json.dumps(CONFIG.__dict__, indent=4)
  f = open(CONFIG_FILE, 'w')
  f.write(s)
  f.close()

def load_configuration():
  try:
    global CONFIG
    if not os.path.exists(CONFIG_FILE):
      write_configuration()
    f = open(CONFIG_FILE, 'r')
    s = f.read()
    CONFIG.__dict__ = json.loads(s)
    f.close()
  except:
    pass

def ask_question(question, rettype, default):
  while True:
    try:
      ret = raw_input(question)
      if len(ret) == 0:
        print('Empty answer given, using default value of {}'.format(default))
        return default

      if rettype == "int":
        intret = int(ret)
        return intret
      elif rettype == "boolean":
        if ret == 'y':
          return True
        elif ret == 'n':
          return False
        print('Please respond y or n..')
        continue
      elif rettype == "directory":
        dirname = os.path.dirname(os.path.realpath(ret))
        if os.path.isdir(dirname):
          return ret
        print("Not existing directory. Please try again...")
        continue
      else:
        return ret
    except ValueError:
      print("Not a valid " + rettype + ". Please try again..")
      continue
    else:
      break

def configure():
  print('Worktime automator configuration')
  print('--------------------------------')
  print('Empty answers will default to current configuration setting')
  global CONFIG
  CONFIG.filename = ask_question("Filename to save work hour log: ", "directory", CONFIG.filename)
  CONFIG.daily_work_minutes = ask_question("Daily work time in minutes: ", "int", CONFIG.daily_work_minutes)
  CONFIG.daily_break_minutes = ask_question("Daily break time in minutes: ", "int", CONFIG.daily_break_minutes)
  CONFIG.notifications = ask_question("Do you want notifications (y/n): ", "boolean", CONFIG.notifications)
  CONFIG.lock_break = ask_question("Is locking screen considered to be break time (y/n): ", "boolean", CONFIG.lock_break)
  write_configuration()
  print('Configuration saved to {}!'.format(CONFIG_FILE))

def is_windows():
  return os.name == 'nt'

# Display notification in UI
def notify(title, text, subtitle = None):
  if CONFIG.notifications is False:
    return

  if is_windows():
    # TODO: Windows notifications
    return

  # MAC notifications
  if subtitle is None:
    os.system("""
              osascript -e 'display notification "{}" with title "{}" sound name "Submarine"'
              """.format(text, title))
  else:
    os.system("""
              osascript -e 'display notification "{}" with title "{}" subtitle "{}" sound name "Submarine"'
              """.format(text, title, subtitle))


# Get csv data as list from file
def get_data(filename):
  if not os.path.exists(filename):
    f = open(filename, 'w')
    f.close()
    return []

  f = open(filename, 'r')
  reader = csv.reader(f, delimiter=';')
  row_data = [line for line in reader]
  f.close()
  return row_data

# Check if screen is locked
def is_screen_locked():
  if is_windows():
    # TODO: Needs testing..
    user32 = ctypes.windll.User32
    return user32.GetForegroundWindow() % 10 == 0
  else:
    data = Quartz.CGSessionCopyCurrentDictionary()
    return data.get('CGSSessionScreenIsLocked', 0) == 1

# Remove headers and footer from csv data
def remove_headers_and_footer(row_data):
  if len(row_data) == 0:
    return row_data

  if row_data[0][IDX_DATE] == 'Date':
    del row_data[0]

  last_row_index = len(row_data) - 1
  if row_data[last_row_index][IDX_DATE] == 'Total':
    del row_data[-1]

  return row_data

# Get current date as string
def get_current_date():
  return datetime.today().strftime(CONFIG.date_format)

# Get current time as string
def get_current_time():
  return datetime.now().strftime(CONFIG.time_format)

# Check if work time is started today
def is_started_today(row_data):
  started_today = False
  todaystr = get_current_date()
  for i, row in enumerate(row_data):
    if row[0] == todaystr:
      started_today = True
      break
  return started_today

def get_index(row_data, date):
  idx = -1
  for i, row in enumerate(row_data):
    if row[IDX_DATE] == date:
      idx = i
      break
  return idx

# Get index of today in the csv data
def get_today_index(row_data):
  todaystr = get_current_date()
  return get_index(row_data, todaystr)

# Add header for explanation
def add_header(row_data):
  row_data.insert(0, ['Date', 'Start', 'End', 'Overtime', 'Type', 'Break time', 'Work time', 'Status'])
  return row_data

# Add footer with total overtime
def add_footer(row_data):
  total_seconds = 0
  for row in row_data:
    if row[0] == 'Date':
      continue
    total_seconds = total_seconds + (int(row[IDX_OT]) * 60)

  minutes = int(divmod(total_seconds, 60)[0])
  hours = float(minutes) / float(60)
  row_data.append(['Total', '', '', str(minutes) + 'min', "{0:.2f}".format(hours) + 'h'])
  return row_data

# Write data to csv file
def write_data(filename, row_data):
  f = open(filename, 'w')
  writer = csv.writer(f, delimiter=';')
  writer.writerows(row_data)
  f.close()

# Start work time
def start_work_time(row_data):
  currenttime = get_current_time()
  breaks = str(CONFIG.daily_break_minutes)
  worktime = str(CONFIG.daily_work_minutes)
  if is_weekend():
    breaks = '0'
    worktime = '0'

  row_data.append([get_current_date(), currenttime, currenttime, '00', 'A', breaks, worktime, 'Ongoing'])
  notify("Work time", "Good morning! Work time started at " + currenttime)
  return row_data

# Check if work time has changed manually
def is_changed_manually(row_data):
  i = get_today_index(row_data)
  if i < 0:
    return False
  row = row_data[i]
  if len(row) < 5:
    row[IDX_TYPE] = 'A'
  return row[IDX_TYPE] == 'M'

# Calculate flex for single date
def calculate_flex(row_data, date):
  i = get_index(row_data, date)
  if i < 0:
    return row_data

  break_time = int(row_data[i][IDX_BREAK]) * 60
  work_time = int(row_data[i][IDX_WORKTIME]) * 60

  ending = date_parser.parse(date + " " + row_data[i][IDX_END])
  starting = date_parser.parse(date + " " + row_data[i][IDX_START])
  elapsed = ending - starting
  seconds = elapsed.total_seconds() - work_time - break_time

  minutes = int(divmod(seconds, 60)[0])
  row_data[i][IDX_OT] = str(minutes)
  return row_data

# Set end time for current date
def set_endtime(row_data):
  todaystr = get_current_date()
  currenttime = get_current_time()
  i = get_today_index(row_data)
  row_data[i][IDX_END] = currenttime
  row_data = calculate_flex(row_data, todaystr)
  return row_data

# End work time
def end_work_time(row_data):
  i = get_today_index(row_data)
  if row_data[i][IDX_STATUS] == 'Ended' or row_data[i][IDX_TYPE] != 'A':
    return row_data

  row_data = set_endtime(row_data)
  row_data[i][IDX_STATUS] = 'Ended'
  return row_data

def add_lock_break(row_data):
  i = get_today_index(row_data)
  currenttime = get_current_time()
  date = get_current_date()
  ending = date_parser.parse(date + " " + row_data[i][IDX_END])
  now = date_parser.parse(date + " " + currenttime)
  elapsed = now - ending
  minutes = int(divmod(elapsed.total_seconds(), 60)[0])
  row_data[i][IDX_BREAK] = str(int(row_data[i][IDX_BREAK]) + minutes)

  row_data = calculate_flex(row_data, date)

  left = ''
  flex = float(row_data[i][IDX_OT]) / float(60)
  if flex > 0:
    left = 'You are done today! Over time for today is {0:.2f}h'.format(flex)
  else:
    left = 'You still have {0:.2f}h to work today'.format(-flex)

  notify('Work time', 'Added automatic break of {} minutes'.format(minutes), left)
  return row_data

# Resume work time
def resume_work_time(row_data):
  i = get_today_index(row_data)
  row_data = set_endtime(row_data)
  if row_data[i][IDX_STATUS] != 'Ongoing':
    if CONFIG.lock_break is True:
      row_data = add_lock_break(row_data)
    else:
      notify_left_worktime(row_data)
  row_data[i][IDX_STATUS] = 'Ongoing'
  return row_data

def notify_left_worktime(row_data):
  i = get_today_index(row_data)
  flex = float(row_data[i][IDX_OT]) / float(60)
  if flex > 0:
    notify('Work time', 'You are done for today! Over time for today is {0:.2f}h'.format(flex))
  else:
    notify('Work time', 'You still have {0:.2f}h to work today'.format(-flex))

# Notify time left for today hourly
def notify_hourly(row_data):
  i = get_today_index(row_data)
  started = parse_time(row_data[i][IDX_START])
  if started.strftime('%M') == datetime.now().strftime('%M') and row_data[i][IDX_STATUS] == 'Ongoing':
    notify_left_worktime(row_data)

# Parse time from str
def parse_time(dur_str):
  if len(dur_str) == 0 or dur_str == 'now':
    return datetime.now()

  todaystr = get_current_date()
  return date_parser.parse(todaystr + " " + dur_str)

# Check if data has changed
def is_changed(original, new):
  if len(original) != len(new):
    return True

  for i in range(len(original)):
    if original[i] != new[i]:
      return True

  return False

# Handle automatic lock/unlock work time
def handle_automatic(row_data):
  if is_changed_manually(row_data):
    return row_data

  started_today = is_started_today(row_data)
  if is_screen_locked():
    if started_today:
      row_data = end_work_time(row_data)
  else:
    if not started_today:
      row_data = start_work_time(row_data)
    else:
      notify_hourly(row_data)
      row_data = resume_work_time(row_data)

  return row_data

# Add flex for specific date
def add_flex(row_data, flex_date):
  formatted_date = flex_date.strftime(CONFIG.date_format)
  currenttime = get_current_time()
  minutes = -CONFIG.daily_work_minutes
  print('Flexing {} with {} minutes'.format(formatted_date, minutes))
  i = get_index(row_data, formatted_date)
  if i >= 0:
    row_data[i][IDX_START] = currenttime
    row_data[i][IDX_END] = currenttime
    row_data[i][IDX_OT] = str(minutes)
    row_data[i][IDX_TYPE] = 'F'
  else:
    row_data.append([formatted_date, currenttime, currenttime, str(minutes), 'F', str(CONFIG.daily_break_minutes), str(CONFIG.daily_work_minutes)])
  return row_data

# Modify start time of the day
def modify_start(row_data, date, start_time):
  formatted_date = date.strftime(CONFIG.date_format)
  formatted_time = start_time.strftime(CONFIG.time_format)
  print('Modifying start time of {} to {}'.format(formatted_date, formatted_time))
  i = get_index(row_data, formatted_date)
  if i >= 0:
    row_data[i][IDX_START] = formatted_time
  else:
    row_data.append([formatted_date, formatted_time, formatted_time, '00', 'A', str(CONFIG.daily_break_minutes)])
  row_data = calculate_flex(row_data, formatted_date)
  return row_data

# Modify end of the day
def modify_end(row_data, date, end_time):
  formatted_date = date.strftime(CONFIG.date_format)
  formatted_time = end_time.strftime(CONFIG.time_format)
  print('Modifying end time of {} to {}'.format(formatted_date, formatted_time))
  i = get_index(row_data, formatted_date)
  if i >= 0:
    row_data[i][IDX_END] = formatted_time
    row_data[i][IDX_TYPE] = 'M'
  else:
    row_data.append([formatted_date, formatted_time, formatted_time, '00', 'M', str(CONFIG.daily_break_minutes), str(CONFIG.daily_work_minutes)])
  row_data = calculate_flex(row_data, formatted_date)
  return row_data

def add_break(row_data, date, time):
  formatted_date = date.strftime(CONFIG.date_format)
  if time > 0:
    print('Adding {} minute break to {}'.format(time, formatted_date))
  else:
    print('Removing {} minutes from break time of {}'.format(-time, formatted_date))
  i = get_index(row_data, formatted_date)
  if i >= 0:
    row_data[i][IDX_BREAK] = str(int(row_data[i][IDX_BREAK]) + time)
  else:
    formatted_time = get_current_time()
    row_data.append([formatted_date, formatted_time, formatted_time, '00', 'M', str(CONFIG.daily_break_minutes + time), str(CONFIG.daily_work_minutes)])

  print('Total brakes {} is {} minutes'.format(formatted_date, row_data[i][IDX_BREAK]))
  row_data = calculate_flex(row_data, formatted_date)
  return row_data

def set_worktime(row_data, date, time):
  formatted_date = date.strftime(CONFIG.date_format)
  print('Setting work time to {} minutes for {}'.format(time, formatted_date))
  i = get_index(row_data, formatted_date)
  if i >= 0:
    row_data[i][IDX_WORKTIME] = str(time)
  else:
    formatted_time = get_current_time()
    row_data.append([formatted_date, formatted_time, formatted_time, '00', 'M', str(CONFIG.daily_break_minutes), str(time)])

  row_data = calculate_flex(row_data, formatted_date)
  return row_data

def is_weekend():
  return datetime.today().weekday() >= 5

def recalculate(row_data):
  for row in row_data:
    print('Recalculating {}'.format(row[IDX_DATE]))
    row_data = calculate_flex(row_data, row[IDX_DATE])
  return row_data

def end_previous(row_data):
  currentdate = get_current_date()
  for row in row_data:
    if row[IDX_DATE] != currentdate:
      row[IDX_STATUS] = 'Ended'
  return row_data

def ensure_columns(row_data):
  for row in row_data:
    if len(row) < 5:
      row.append('A')
    if len(row) < 6:
      row.append(str(CONFIG.daily_break_minutes))
    if len(row) < 7:
      row.append(str(CONFIG.daily_work_minutes))
    if len(row) < 8:
      row.append('Ended')
  return row_data

# Main
def main():
  load_configuration()
  args = parse_args()
  if args.config is True:
    configure()
    return

  filename = args.filename

  row_data = get_data(filename)
  row_data = remove_headers_and_footer(row_data)
  row_data = ensure_columns(row_data)
  original_data = copy.deepcopy(row_data)

  if args.recalculate is True:
    row_data = recalculate(row_data)

  if args.flex is True:
    row_data = add_flex(row_data, args.date)

  if args.start is not None:
    row_data = modify_start(row_data, args.date, args.start)

  if args.end is not None:
    row_data = modify_end(row_data, args.date, args.end)

  if args.addbreakmin is not None and args.addbreakmin > 0:
    row_data = add_break(row_data, args.date, args.addbreakmin)

  if args.removebreakmin is not None and args.removebreakmin > 0:
    row_data = add_break(row_data, args.date, -args.removebreakmin)

  if args.worktime is not None and args.worktime >= 0:
    row_data = set_worktime(row_data, args.date, args.worktime)

  row_data = handle_automatic(row_data)
  row_data = end_previous(row_data)
  row_data = sorted(row_data, key=lambda l:l[0])

  if is_changed(original_data, row_data):
    row_data = add_header(row_data)
    row_data = add_footer(row_data)
    write_data(filename, row_data)

if __name__ == '__main__':
  try:
    main()
  except KeyboardInterrupt:
    print('Interrupted by user!')

# Automatic work hour logging (MacOS)

This simple script checks when your screen is locked and automatically writes
down to csv file the starting and ending of your work day. The automation is
based on plist launch daemon.

The start is marked when you first time unlock your computer and end will be the
time you last time lock your computer.

You can try it out just by running the worktime.py file

```bash
python worktime.py
```

## Setup

### MacOS

1. Copy fi.drodil.worktime.plist file to ~/Library/LaunchAgents

```bash
cp fi.drodil.worktime.plist ~/Library/LaunchAgents
```

2. Modify from the plist file the program arguments:

```bash
$EDITOR ~/Library/LaunchAgents/fi.drodil.worktime.plist
```

```xml
<array>
    <string>python</string>
    <string>**ABSOLUTE LOCATION OF worktime.py FILE**</string>
</array>
```

3. Authorize the worktime.py to read your current UI session

```bash
security authorize -u worktime.py
```
4. Install worktime

```bash
python setup.py install
```

4. Run the one-time configuration of the tool

```bash
python worktime.py --config
python worktime.py --help
```

5. Load the plist to launctl

```bash
cd ~/Library/LaunchAgents
launchctl load fi.drodil.worktime.plist
```

6. Check if the work day starts. Lock your computer and wait for one minute;
   check if the work day ends.

### Windows

Add scheduled task to run worktime every minute

```bash
schtasks /create /tn "Work Time" /sc minute /mo 1 /tr "python <PATH TO THIS REPOSITORY>/worktime.py"
```

**NOTE: This is not tested! Might need a batch script**

## Uninstalling

To uninstall, just remove the files and unload the plist:

```bash
cd ~/Library/LaunchAgents
launchctl unload fi.drodil.worktime.plist
rm fi.drodil.worktime.plist
```

## Configuration

When you run worktime.py with --config option, it will create and save a
configuration file called config.json (if necessary).

This configuration defines the default daily work and break time, format to use
for dates and times as well if screen locking is considered to be a break in the
middle of the day.

You can modify this file manually or using the --config option. If you do
changes manually, please make sure the configuration options are still valid.

## Manual usage

### Options

You can also use other functionalities by passing parameters to the script. You
can specify filename to do actions as last parameter of the script but if you
leave it out, default file from configuration file will be used.

Available commands are:

* -d|--date
  * Date for manual actions like start/end/flex
  * Default is today
* -f|--flex
  * Add flex day to given date (-d or --date)
* -s|--start [time]
  * Modify start time of given date (-d or --date)
  * Default is now
* -e|--end [time]
  * Modify end time of given date (-d or --date)
  * Default is now
* -ab|--add-break [time]
  * Add break time in minutes to given date (-d or --date)
* -rb|--remove-break [time]
  * Remove break time in minutes from given date (-d or --date)
* --recalculate
  * Recalculate work time in given file
* --config
  * Run configuration for the tool for static settings

More information can be found from --help command

### Add to PATH (MacOS / Linux)

To more easily handle your worktime with this script, you should add it to your
PATH variable for example like this:

```bash
cd
mkdir bin
cd bin
ln -s <LOCATION OF worktime.py> worktime
echo ""export PATH=\"~/bin/;$PATH\"" >> ~/.profile
```

## Contributing

You are free to contribute to this project by creating code reviews. Please see
below TODO list for possible ideas what to implement.

## TODO

Additional features could be done to include:

* Automatic install script (.sh or .py)
  * Copy .plist
  * Change plist argument values according to location of this repository
  * Ask for where to save the hour report and add it to plist argument value
*  Windows support
  * Screen lock support should be in place
  * Notification support missing
  * Installation instructions
  * Add to path instructions
  * No Windows machine so cannot test, **contributions welcome**!
* Linux support :o

## Q&A

* Why?
  * Because keeping up with work hours manually is painful and I want to have my
    flex hours up somewhere
* Can I modify the list manually?
  * Yes you can. The tool will not touch the existing rows, only the row that
    matches today. Also it will not write the file unnecessarily so even though
    it checks this once every minute through plist, you are free to modify the
    file when your computer is unlocked
* What does Type mean?
  * A = Automatically tracked work time
  * M = Manually overridden work time
  * If type is Manual, the end time will not be automatically updated when you
    lock your computer
* Why python2 over python3?
  * Quartz module is required to check for screen lock. It might be available
    for python3 but would require additional installations

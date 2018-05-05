#!/bin/sh

# Delete files older than 100 days.
# Cronjob running under "sudo crontab -e"
# add a line like:
# 15 0 * * * sh /home/leon/MARTAS/UtilityScripts/cleanup.sh
# to run the job every day 15 minutes past midnight
DATE="/bin/date"
ECHO="/bin/echo"
DAYS=100
MARTAS='/home/cobs/MARTAS'
# make a permanent vaiable in environment
MLOG="$MARTAS/Logs/cleanup.log"

$ECHO "Running cleanup ... and deleting data older than $DAYS days:" > $MLOG
$DATE >> $MLOG
find /srv/ws -name "*.bin" -mtime +100 -exec rm {} \;
$ECHO "... finished" >> $MLOG


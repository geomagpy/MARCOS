#!/bin/sh


### Restarting collector regularly
### ###############################

# Please note, as users my change (manual start, croned schedules)
# make the log file writeable for all users (please update the path)
MARCOS='/home/cobs/MARCOS'
# make a permanent vaiable in environment

MLOG="$MARCOS/Logs/marcos.log"
RLOG="$MARCOS/Logs/restart.log"
chmod 666 $MLOG
/etc/init.d/collector-martas1 restart > $RLOG 2>&1
/etc/init.d/collector-martas2 restart >> $RLOG 2>&1


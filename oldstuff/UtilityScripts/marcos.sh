#! /bin/sh
### BEGIN INIT INFO
# Provides:          marcos
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Starts the MARCOS/collector_moon.py script
# Description:       see short
#                    
### END INIT INFO

# /etc/init.d/marcos

# Some things that run always
touch /var/lock/marcos

# Carry out specific functions when asked to by the system
case "$1" in
  start)
    echo "Starting collector script marcos (in 30sec)"
    echo "--------------------"
    sleep 30 # should be 60
    echo "initiating MARCOS"
    python /home/cobs/MARCOS/collector_moon.py &
    ;;
  stop)
    echo "Stopping collector script marcos"
    echo "--------------------"
    ps -ef | grep 'collector_moon.py' | awk '{print $2}' | xargs kill -9
    ;;
  restart)
    echo "Stopping collector script marcos"
    echo "--------------------"
    ps -ef | grep 'collector_moon.py' | awk '{print $2}' | xargs kill -9
    echo "Restarting collector script marcos"
    echo "--------------------"
    echo "initiating MARCOS"
    python /home/cobs/MARCOS/collector_moon.py &
    ;;
  *)
    echo "Usage: /etc/init.d/marcos {start|stop}"
    exit 1
    ;;
esac

exit 0

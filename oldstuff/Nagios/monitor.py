#!/usr/bin/python

"""
monitor.py :
Check for the presence of new data within the database. You need to provide a list of 
sensor IDs. Requires MagPy >= 0.1.296. 
"""
from __future__ import print_function
import sys, getopt
from os.path import expanduser  

from magpy.database import *
from magpy.opt import cred as mpcred

dbdateformat = "%Y-%m-%d %H:%M:%S.%f"

def monitorlogfile(path,linetodrop,linetoadd,date):
    # 0. Test whether directory is existing
    print(("Accessing Monitor log file:", linetodrop, linetoadd))

    # 1. Read file
    tester = []
    try:
        f = open(path, 'rb')
        tester = [line.strip() for line in f]
        for line in tester:
            if line.startswith(linetoadd):
               tester = []
               break
        #if linetoadd in tester:
        #    tester = []
        f.close()
    except:
        print("Logfile not yet existing - creating it:")
        f = open(path, 'wb')
        f.write(linetoadd+'\n')
        f.close()
        return
    
        
    if len(tester)>0:
        # modify file
        f = open(path, 'wb')
        # 2. Drop line
        newlines = [elem for elem in tester if not elem.startswith(linetodrop) and not elem.startswith(linetoadd)]
        # 3. Append new line
        if linetoadd.find('since') > 0:
            linetoadd = linetoadd + ' ' + date
        newlines.append(linetoadd)
        # 4. Write log file
        for line in newlines:
            f.write(line+'\n')
        f.close()
    else:
        # nothing to do - leave file unchanged
        print("nothing to do - leaving file unchanged")
        return

def main(argv):

    homedir = expanduser("~")

    printsensors = False
    cred = ''
    sensors = ''
    exclude = ''
    logfile = os.path.join(homedir,'MARCOS','Logs','monitor.log')
    timerange = 30
    currenttime = datetime.utcnow()
    try:
        opts, args = getopt.getopt(argv,"hc:ps:e:l:t:",["credentials=","sensors=","logfile=","timerange=",])
    except getopt.GetoptError:
        print('monitor.py -c <credentialshortcut> -p <print> -p <print> -s <sensors> -e <exclude> -l <logfile> -t <timerange>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('Checking data base whether within a given time period new data has arrived for the')
            print('selected sensor IDs. Function is using utc time.')
            print('-------------------------------------')
            print('Usage:')
            print('monitor.py -c <credentialshortcut> -p <print> -s <sensors>')
            print('  -e <exclude> -l <logfile> -t <timerange>')
            print(' ')
            print('-------------------------------------')
            print('Options:')
            print('-c       : shortcut to access stored information')
            print('-p       : print a list of available sensor IDs from data base')
            print('-s       : comma separted list of sensor IDs')
            print('-e       : comma separted list of sensor IDs to exclude from test')
            print('-l       : log file with full path - default is the /MARCOS/Logs/monitor.log')
            print('           directory within the current users home')
            print('-t       : time range of acceptable age of data in minutes - default is 30')
            print('-------------------------------------')
            print('Examples:')
            print('python monitor.py -c cobs -s LEMI025_22_0001,POS1_N432_0001 -t 60 ')
            print('!!!!  please note: put path in quotes !!!!!!')
            sys.exit()
        elif opt in ("-p", "--print"):
            printsensors = True
        elif opt in ("-c", "--cred"):
            cred = arg
        elif opt in ("-l", "--logfile"):
            logfile = arg
        elif opt in ("-s", "--sensors"):
            sensors = arg
        elif opt in ("-e", "--exclude"):
            exclude = arg
        elif opt in ("-t", "--timerange"):
            try:
                timerange = int(arg)
            except:
                print("timerange needs to be an integer") 
                sys.exit()

    if cred == '':
        print('Specify (and remember) a shortcut using the -c option:')
        print('-- check addcred.py -h for more options and requirements')
        sys.exit()

    print("Accessing data bank ...")
    try:
        db = mysql.connect(host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        print("success")
    except:
        print("failure - check your credentials")
        sys.exit()

    if printsensors:
        print('List of Sensor IDs within your data base')
        print('-- ignoring all other eventually given options')
        listofsensors = dbselect(db, 'SensorID', 'SENSORS')
        print(listofsensors)
        sys.exit()

    if sensors == '':
        print('No Sensors specified - using full sensor list from MARCOS DB')
        senslst = dbselect(db, 'SensorID', 'SENSORS')
    else:
        try:
            if sensors.index(',') > 0:
                senslst = sensors.split(',')  # split up list of sensors
                senslst = [elem.strip() for elem in senslst]
            else:
                senslst = [sensors]
        except:
            print("Error while interpreting sensor list")
            print('-- check monitor.py -h for more options and requirements')
            sys.exit()

    if not exclude == '':
        try:
            if exclude.find(',') > 0:
                excludelst = exclude.split(',')  # split up list of sensors
                excludelst = [elem.strip() for elem in excludelst]
            else:
                excludelst = [exclude]
            print(excludelst)
        except:
            print("Error while interpreting exclude list")
            print('-- check monitor.py -h for more options and requirements')
            sys.exit()

        senslst = [elem for elem in senslst if not elem in excludelst]

    # Now get the available data tables for the selected sensors
    try:
        datatabs = []
        for sens in senslst:
            sql = 'SensorID = "'+sens+'"'
            print(sql)
            sensdatatabs = dbselect(db, 'DataID','DATAINFO',sql)
            datatabs.extend(sensdatatabs)
    except:
        print("Error while checking for available data tables")
        sys.exit()

    print("Timerange:", timerange)
    print("Amount of tables", len(datatabs))

    if not len(datatabs) > 0:
        print("Did not find any data table for your specified sensors. Please check your list, database credentials")
        sys.exit()

    # Now get the latest input for each sensor in all tables
    #try:
    for sens in senslst:
        print("Checking Sensor:", sens)
        lasttime = datetime(1900,1,1) # Check for a significant date after 1900
        for table in datatabs:
            if table.startswith(sens):
                print(" - Found table", table)
                last = dbselect(db,'time',table,expert="ORDER BY time DESC LIMIT 1")
                #print len(last), table
                if len(last) > 0:
                    lastval = datetime.strptime(last[0],dbdateformat)
                    # convert last to datetime
                    if lastval > lasttime:
                        lasttime = lastval

        if currenttime-timedelta(minutes=timerange) > lasttime:
            # add info to log (write a log function which first checks logfile whether this info is new
            # info could be like "SensorID": no new data available since "lasttime"
            # remove any line like "SensorID": data transmission in time
            dropline = sens + ": data transmission in time"
            addline = sens + ": no new data available since"
            date = datetime.strftime(lasttime,"%Y-%m-%dT%H:%M:%S")
            monitorlogfile(logfile,dropline, addline, date)
        else:
            # check logfile and remove any Line like "SensorID": no new data available since "lasttime"
            # Append "SensorID": data transmission in time
            addline = sens + ": data transmission in time"
            dropline = sens + ": no new data available since"
            date = datetime.strftime(lasttime,"%Y-%m-%dT%H:%M:%S")
            monitorlogfile(logfile,dropline, addline, date)
    #except:


if __name__ == "__main__":
   main(sys.argv[1:])



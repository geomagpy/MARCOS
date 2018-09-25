#!/usr/bin/env python
"""
Setting up a clean new database from raw data 


TODO: either modify cleanup or write a small job to extract critical errors to a separate log file for NAGIOS
"""
try:
    from magpy.stream import *
    from magpy.database import *
    from magpy.opt import cred as mpcred
except:
    import sys
    sys.path.append('/home/leon/Software/magpy/trunk/src')
    from stream import *
    from database import *
    from opt import cred as mpcred
import getopt
import pwd

def main(argv):
    shortcut = ''
    path = ''
    depth = 2
    autofilter = 3
    flagging = False
    startdate = ''    
    archiveformat = 'PYCDF'
    flaglist = []
    skip = ''
    samplingrateratio=12 # 12 days * samplingperiod (sec) will be kept from today (e.g. 12 days of seconds data. 720 days of minute data.
    try:
        opts, args = getopt.getopt(argv,"hc:p:b:d:s:gi:a:",["cred=","path=","begin=","depth=","skip=","flag=","sr=","autofilter=",])
    except getopt.GetoptError:
        print 'cleanupDB.py -c <cred> -p <archivepath> -b <begin> -d <depth> -s <skip> -g <flag> -i <sr> -a <autofilter>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '-------------------------------------'
            print 'Description:'
            print '-- cleanupDB.py uploads data to a databank,  --'
            print 'Accesses data within the selected data bank and created '
            print 'filtered records. Old database entries exceding a defined age'
            print 'are deleted. Optionally archive files can be stored in a user defined format.'
            print 'By default filtered data sets are created and added into the DB.'
            print 'Depending on sampling rate second, minute, and hourly data sets '
            print 'are created using recommended gaussian filters for seconds '
            print 'and minutes, as well as flat means for hourly data (INTERAMGNET '
            print 'technical manual vers. 4.6 and IAGA guide).'
            print 'Futhermore, the databank size is automatically restricted '
            print 'in dependency of the sampling rate of the input data. Only the last '
            print '12 days of second data, the last 720 days of minute data and '
            print 'approximately 118 years of hourly data are kept. To modify these default'
            print 'settings please contact the developers (or learn python and'
            print 'edit the code - its simple and the MagPy cookbook will help you).'
            print '-------------------------------------'
            print 'Usage:'
            print 'cleanupDB.py -c <cred> -p <archivepath> -b <begin> -d <depth> -s <skip> -g <flag> -i <sr> '
            print '-------------------------------------'
            print 'Options:'
            print '-c (required) : provide the shortcut to the data bank credentials as returned by setupDB.py'
            print '-p            : archivepath like "/home/max/myarchive"'
            print '              : please note: an asterix requires quotes'
            print '-d            : depth'
            print '-b            : begin: end = begin - depth(days)'
            print '-f            : archive format - default is PYCDF'
            print '-s            : list sensor ids to skip, comma separated'
            print '-g (no input) : flagged data (to be removed - 1,3) is removed before filtering.'
            print '              : Raw data remains untouched.'
            print '-i            : samplingrateratio for deleting old db entries - default is 12:'
            print '              : deleting data older than samplingrate(sec)* 12 days.'
            print '-a            : automatically apply IAGA recommended filtering if possible '
            print '              : and save to db and archive. Options:'
            print '              : 0 - no filtering' 
            print '              : 1 - create filtered second data' 
            print '              : 2 - create filtered secs, min' 
            print '              : 3 - create filtered secs, min, hour (default)' 
            print '-------------------------------------'
            print 'Example:'
            print 'every day cron job: python cleanupDB.py -c cobsdb -p /srv/archive'
            print 'creating archive of old db entries: python cleanupDB.py -c cobsdb -p /media/Samsung/Observatory/data/ -d 30 -b "2012-06-01" -g -i 100 -a 3'
            sys.exit()
        elif opt in ("-c", "--cred"):
            cred = arg
        elif opt in ("-p", "--archivepath"):
            path = arg
        elif opt in ("-b", "--begin"):
            startdate = arg
        elif opt in ("-d", "--depth"):
            try:
                depth = int(arg)
                if not depth >= 2:
                    print "depth needs to be positve" 
                    sys.exit()
            except:
                print "depth needs to be an integer" 
                sys.exit()
        elif opt in ("-f", "--archiveformat"):
            archiveformat = arg
        elif opt in ("-g", "--flag"):
            flagging = True
        elif opt in ("-s", "--skip"):
            skip = arg
        elif opt in ("-i", "--samplingrateratio"):
            try:
                samplingrateratio = int(arg)
            except:
                print "samplingrateratio needs to be an integer" 
                sys.exit()
        elif opt in ("-a", "--autofilter"):
            try:
                autofilter = int(arg)
                if not autofilter in [0,1,2,3]:
                    print "autofilter needs to be in the range of 0,1,2,3" 
                    sys.exit()
            except:
                print "autofilter needs to be one of 0,1,2,3" 
                sys.exit()

    if cred == '':
        print 'Specify a shortcut to the credential information by the -c option:'
        print '-- check data2DB.py -h for more options and requirements'
        sys.exit()

    print "Accessing data bank ..."
    try:
        db = mysql.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        print "success"
    except:
        print "failure - check your credentials / databank"
        sys.exit()

    # Getting dates
    datelist = []
    if startdate == '':
        current = datetime.utcnow() # make that a variable
    else:
        current = DataStream()._testtime(startdate)

    newcurrent = current
    for elem in range(depth):
        datelist.append(datetime.strftime(newcurrent,"%Y-%m-%d"))
        newcurrent = current-timedelta(days=elem+1)

    print "Dealing with time range:", datelist

    testdate = datetime.strftime((datetime.strptime(min(datelist),"%Y-%m-%d")-timedelta(days=1)),"%Y-%m-%d")

    # get a list with all datainfoids covering the selected time range
    sql = 'SELECT DataID FROM DATAINFO WHERE DataMaxTime > "'+testdate+'" AND  DataMinTime < "'+max(datelist)+'"'

    # skip BLV measurements from cleanup 
    sql = sql + ' AND SensorID NOT LIKE "BLV_%"'
    # skip Quakes from cleanup 
    sql = sql + ' AND SensorID NOT LIKE "QUAKES"'

    if len(skip) > 0:
        skipstr = ''
        skiplst = skip.split(',')
        for sensortoskip in skiplst:
            skipstr += ' AND SensorID != "'+sensortoskip+'"'
        sql = sql + skipstr
        print sql
 
    cursor = db.cursor ()
    try:
        cursor.execute(sql)
    except:
        print "Error when reading database"
    datainfoidlist = [elem[0] for elem in cursor.fetchall()]

    print "Cleaning database contens of:", datainfoidlist

    for data in datainfoidlist:
        print " ---------------------------- "
        print " ---------------------------- "
        print "Loading data files of", data
        print " ---------------------------- "
        print " ---------------------------- "
        print datetime.utcnow()
        try:
            if not startdate == '':
                stream = readDB(db,data,min(datelist),max(datelist))
            else:
                stream = readDB(db,data,min(datelist),None)
        except:
            stream = DataStream()
            print (" Error: Could not read database contents of {}".format(data))
        keys = stream._get_key_headers()
        lenstream = stream.length()[0]
 
        if lenstream > 1:
            print "  Found data points:", lenstream
            print datetime.utcnow()
            print "  Starting from :", num2date(min(stream.ndarray[0]))
            if not num2date(max(stream.ndarray[0])).replace(tzinfo=None) < datetime.utcnow().replace(tzinfo=None):
                print ("  Found in-appropriate date in stream!! maxdate = {}".format(num2date(max(stream.ndarray[0]))))
                print ("  Length stream before:", len(stream.ndarray[0]))
                stream = stream.extract('time',date2num(datetime.utcnow()),'<')
                print ("  Length stream after:", len(stream.ndarray[0]))
            print "  Ending at :", num2date(max(stream.ndarray[0]))

            sr = stream.samplingrate()
            print "  Sampling rate:", sr

            if not path == '':
                try:
                    sensorid = stream.header['SensorID']
                    stationid = stream.header['StationID']
                    datainfoid = stream.header['DataID']
                    archivepath = os.path.join(path,stationid,sensorid,stream.header['DataID'])
                except:
                    print "Obviously a problem with insufficient header information"
                    print " - check StationID, SensorID and DataID in DB"
                print "Archiving unfiltered data of ", data
                stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=archiveformat)
            if not isnan(sr):
                print "Now deleting old entries in database older than %s days" % str(int(sr*samplingrateratio))
                dbdelete(db,stream.header['DataID'],samplingrateratio=samplingrateratio)

            print ("Please note: flags are not contained in the cdf archive. They are stored separately in the database (and yearly files -> too be done")
            #if flagging and db and sr > 0.9:
            #    print "Applying flags (only 1 Hz data and below)", datetime.utcnow()
            #    flaglist = db2flaglist(db,sensorid=stream.header['SensorID'])
            #    if len(flaglist) > 0:
            #        for i in range(len(flaglist)):
            #            stream = stream.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])

            #    print "Flagging finished", datetime.utcnow()
            #print sensorid, len(stream)

            if sr < 0.8 and autofilter in [1,2,3]: #changed from 0.9 to 0.8 may 2018
                print "Filtering to 1Hz"
                try:
                    if flagging:
                        stream = stream.remove_flagged()
                    print "Filtering keys", keys
                    stream = stream.filter(missingdata='conservative')
                    if flagging:
                        print ("Please note: flags are not contained in the cdf archive. They are stored separately in the database (and yearly files -> too be done")
                        #print "Applying flags (only 1 Hz data and below)", datetime.utcnow()
                        #flaglist = db2flaglist(db,sensorid=stream.header['SensorID'])
                        #if len(flaglist) > 0:
                        #    for i in range(len(flaglist)):
                        #        stream = stream.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])
                        #print "Flagging finished", datetime.utcnow()

                    print "Writing to DB"
                    writeDB(db,stream)
                except:
                    print "A problem occurred while filtering to 1 second data"
                try:
                    # Now save 1Hz to archive
                    datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
                    if not path == '':
                        archivepath = os.path.join(path,stationid,sensorid,datainfoid)
                        stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=archiveformat)
                except:
                    print "A problem occurred while saving archive file of 1 second data"
                try:
                    dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
                    print "Finished seconds filtering for %s: %s data points " % (datainfoid, stream.length()[0])
                    print datetime.utcnow()
                except:
                    print "A problem occurred while saving archive file of 1 second data"
            if sr < 59.0 and autofilter in [2,3]:
                print "Filtering to minutes"
                try:
                    if flagging:
                        #for i in range(len(flaglist)):
                        #    stream = stream.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])
                        stream = stream.remove_flagged()
                    stream = stream.filter()
                    writeDB(db,stream)
                except:
                    print "A problem occurred while filtering to 1 minute data"
                try:
                    # Now save 1 Minute to archive
                    datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
                    if not path == '':
                        archivepath = os.path.join(path,stationid,sensorid,datainfoid)
                        stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=archiveformat)
                except:
                    print "A problem occurred while saving archive file of 1 minute data"
                try:
                    dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
                    print "Finished minutes filtering for %s: %s data points " % (datainfoid, stream.length()[0])
                except:
                    print "A problem occurred while removing old inputs from database"
            if sr < 3500.0 and autofilter in [3]:
                print "Filtering to hours"
                #try:
                print len(stream)
                if flagging:
                    #print "Flagging now" 
                    #for i in range(len(flaglist)):
                    #    stream = stream.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])
                    stream = stream.remove_flagged()
                stream = stream.filter(filter_width=timedelta(hours=1),filter_type='flat', resampleoffset=timedelta(minutes=30))
                writeDB(db,stream)
                #except:
                #    print "A problem occurred while filtering 1 hour data"
                #    # Now save 1 Hour to archive
                try:
                    datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
                    if not path == '':
                        archivepath = os.path.join(path,stationid,sensorid,datainfoid)
                        stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=archiveformat)
                except:
                    print "A problem occurred while saving archive file of 1 hour data"
                try:
                    dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
                    print "Finished hours filtering for %s: %s data points " % (datainfoid, stream.length()[0])
                except:
                    print "A problem occurred while removing old inputs from database"


if __name__ == "__main__":
   main(sys.argv[1:])




#!/usr/bin/env python
"""
Setting up a clean new database from raw data 
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

def main(argv):
    shortcut = ''
    path = ''
    archivepath = ''
    archiveformat = 'PYCDF'
    sensorid = ''
    stationid = ''
    starttime = ''
    endtime = ''
    inserttable = ''
    samplingrateratio=12 # 12 days * samplingperiod (sec) will be kept from today (e.g. 12 days of seconds data. 720 days of minute data.
    autofill = False
    try:
        opts, args = getopt.getopt(argv,"hc:p:a:s:t:b:e:i:um:",["cred=","path=","archivepath=","sensorid=","stationid=","begin=","end=","sr=","autofill=","inserttable=",])
    except getopt.GetoptError:
        print 'data2DB.py -c <cred> -p <path2data> -a <archivepath> -f <archiveformat> -s <sensorid> -t <stationid> -b <begin> -b <end> -i <sr> -u <autofill> -m <inserttable>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '-------------------------------------'
            print 'Description:'
            print '-- data2DB.py uploads data to a databank --'
            print 'Creates filtered data sets and adds them into the DB.'
            print 'Depending on sampling rate second, minute, and hourly data sets '
            print 'are created using recommended gaussian filters for seconds '
            print 'and minutes, as well as flat means for hourly data (INTERAMGNET '
            print 'technical manual vers. 4.6 and IAGA guide).'
            print 'Futhermore, the databank size is automatically restricted '
            print 'in dependency of the sampling rate of the input data. By default only the last '
            print '12 days of second data, the last 720 days of minute data and '
            print 'approximately 118 years of hourly data are kept.'
            print 'Archive files can also be created. by adding stationID and sensorID to the '
            print 'given path name '
            print '-------------------------------------'
            print 'Usage:'
            print 'data2DB.py -c <cred> -p <path2data> -a <archivepath> -f <archiveformat> -s <sensorid> -t <stationid> -b <begin> -b <end> -i <sr> -u <autofill>'
            print '-------------------------------------'
            print 'Options:'
            print '-c (required) : provide the shortcut to the data bank credentials as returned by setupDB.py'
            print '-p (required) : path to data - like "/home/max/mydata/*" or "/home/max/mydata/*.min"'
            print '              : please note: an asterix requires quotes'
            print '-a            : archivepath: filtered data will be archived to this folder'
            print '-f            : dataformat for archiving: default is PYCDF'
            print '-s            : ID of the sensor (required if not contained in the datas meta information)'
            print '-t            : ID of the station i.e. the Observatory code (required if not in meta data)'
            print '-b            : startdate for upload e.g. 2014-01-01'
            print '-e            : enddate for upload e.g. 2014-02-01'
            print '              : if b,e are missing all matching data within the path will be loaded which may take a long time and also test your systems memory'     
            print '-i            : samplingrateratio for deleting old db entries - default is 12:'
            print '              : deleting data older than samplingrate(sec)* 12 days.'
            print '-u (no input) : fill gaps by linear interpolation - for rcs'
            print '-m            : force unfiltered raw data to the given table name.' 
            print '-------------------------------------'
            print 'Example:'
            print 'python data2DB.py -c cobsdb -p "/archive/WIC/POS1_N432_0001/raw/*.bin" -s POS1_N432_0001 -t WIC -b 2014-01-01 -e 2014-02-01 '
            sys.exit()
        elif opt in ("-c", "--cred"):
            cred = arg
        elif opt in ("-p", "--path"):
            path = arg
        elif opt in ("-a", "--archivepath"):
            archivepath = arg
        elif opt in ("-f", "--archiveformat"):
            archiveformat = arg
        elif opt in ("-s", "--sensorid"):
            sensorid = arg
        elif opt in ("-t", "--stationid"):
            stationid = arg
        elif opt in ("-b", "--begin"):
            starttime = arg
        elif opt in ("-e", "--end"):
            endtime = arg
        elif opt in ("-m", "--inserttable"):
            inserttable = arg
        elif opt in ("-i", "--samplingrateratio"):
            try:
                samplingrateratio = int(arg)
            except:
                print "samplingrateratio needs to be an integer" 
                sys.exit()
        elif opt in ("-u", "--autofill"):
            autofill = True

    if cred == '':
        print 'Specify a shortcut to the credential information by the -c option:'
        print '-- check data2DB.py -h for more options and requirements'
        sys.exit()
    if path == '':
        print 'Specify a data path by the -p option:'
        print '-- check data2DB.py -h for more options and requirements'
        sys.exit()

    print "Accessing data bank ..."
    try:
        db = MySQLdb.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        print "success"
    except:
        print "failure - check your credentials"
        sys.exit()

    try:
        print "Loading data files from", path
        if starttime == '' and endtime == '':
            stream = read(os.path.join(path))
        elif starttime == '':
            stream = read(os.path.join(path),endtime=endtime)
        elif endtime == '':
            stream = read(os.path.join(path),starttime=starttime)
        else:
            print "from", starttime, endtime
            stream = read(os.path.join(path),starttime=starttime,endtime=endtime)
        if len(stream) > 0:
            print "Found data points:", len(stream)
        else:
            print "given data path (ot time range) does not contain MagPy readable data"
            sys.exit()
    except:
        print "unkown problems when reading files"
        sys.exit()

    try:
        try:
            if sensorid == '':
                sensorid = stream.header['SensorID']
        except KeyError:
            if sensorid == '':
                print "SensorsID not in data file - needs to be provided by -s option"
                print '-- check data2DB.py -h for more options and requirements'
                sys.exit()
            pass
        try:
            if stationid == '':
                stationid = stream.header['StationID']
        except KeyError:
            if stationid == '':
                print "StationID not in data file - needs to be provided by -t option"
                print '-- check data2DB.py -h for more options and requirements'
                sys.exit()
            pass
              
        stream.header['SensorID'] = sensorid
        stream.header['StationID'] = stationid
        sr = stream.samplingrate()
        print "Sampling rate for sensor %s: %s sec" % (sensorid,str(sr))
    except:
        print "Extracting basic information failed for unkown reason"
        sys.exit()

    if inserttable == '':
        stream2db(db,stream,mode='replace')
        datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
    else:
        stream2db(db,stream,mode='force',tablename=inserttable)
        datainfoid = inserttable
    keys = stream._get_key_headers()
    if not archivepath == '':
        # add an option to add any existing data base information to the archives header
        apath = os.path.join(archivepath,stationid,sensorid,datainfoid)
        stream.write(apath,filenamebegins=datainfoid+'_',format_type=archiveformat)
    dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
  
    try:
        if sr < 0.9:
            print "Filtering to 1Hz"
            stream = stream.nfilter(keys=keys,filter_width=timedelta(seconds=1),dontfillgaps=True)
            stream2db(db,stream,mode='replace')
            datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
            if not archivepath == '':
                apath = os.path.join(archivepath,stationid,sensorid,datainfoid)
                stream.write(apath,filenamebegins=datainfoid+'_',format_type=archiveformat)
            dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
            print "Finished seconds filtering for %s: %s data points " % (datainfoid, len(stream))
        if sr < 59.0:
            print "Filtering to minutes"
            stream = stream.nfilter(keys=keys,filter_width=timedelta(minutes=1),dontfillgaps=True)
            stream2db(db,stream,mode='replace')
            datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
            if not archivepath == '':
                apath = os.path.join(archivepath,stationid,sensorid,datainfoid)
                stream.write(apath,filenamebegins=datainfoid+'_',format_type=archiveformat)
            dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
            print "Finished minutes filtering for %s: %s data points " % (datainfoid, len(stream))
        if sr < 3500.0:
            print "Filtering to hours"
            stream = stream.nfilter(keys=keys,filter_width=timedelta(hours=1),filter_type='flat', resampleoffset=timedelta(minutes=30),dontfillgaps=True)
            stream2db(db,stream,mode='replace')
            datainfoid = dbdatainfo(db,stream.header['SensorID'],stream.header,updatedb=False)
            if not archivepath == '':
                apath = os.path.join(archivepath,stationid,sensorid,datainfoid)
                stream.write(apath,filenamebegins=datainfoid+'_',format_type=archiveformat)
            dbdelete(db,datainfoid,samplingrateratio=samplingrateratio)
            print "Finished hours filtering for %s: %s data points " % (datainfoid, len(stream))
    except:
        print "Unkown error while writing to data bank"
        sys.exit()

if __name__ == "__main__":
   main(sys.argv[1:])




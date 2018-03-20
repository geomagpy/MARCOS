#!/usr/bin/env python
"""
Get files from a remote server (to be reached by nfs, samba, ftp, html or local directory) 
File content is directly added to a data bank (or local file if preferred).
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
import fnmatch
import pwd
import zipfile


'''
Changelog:
2014-08-02:   RL removed break when no data was found (could happen if at this selected day not data is available. All other days need to be collected however.
2014-10-22:   RL updated the description
2014-11-04:   RL added the inserttable option to force data upload to a specific table (e.g. for rcs conrad data which has a variable sampling rate)
2015-10-20:   RL changes for fast ndarrays and zip option
'''

def walkdir(filepat,top):
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist,filepat):
            yield os.path.join(path,name)


def main(argv):
    creddb = ''
    credtransfer = ''
    protocol = ''
    localpath = ''
    remotepath = ''
    sensorid = ''
    stationid = ''
    startdate = ''
    inserttable = ''
    depth = 1
    fileformat = ''
    flagging=False
    disableproxy=False
    zipping = False
    walk=False
    flaglist = []
    defaultuser = ''
    uppercase=False

    try:
        opts, args = getopt.getopt(argv,"hc:e:l:r:p:s:t:b:d:a:f:gowu:xm:z",["creddb=","credtransfer=","localpath=","sensorid=","stationid=","begin=","end="])
    except getopt.GetoptError:
        print 'collectfile.py -c <creddb> -e <credtransfer> -l <localpath> -r <remotepath> -p <protocol> -s <sensorid> -t <stationid> -b <startdate> -d <depth> -a <dateformat> -f <filefomat> -g <flag> -o <disableproxy=True> -w <walk=True> -u <user> -x <uppercase> -m <insert-table> -z <zip>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '-------------------------------------'
            print 'Description:'
            print 'collectfile.py reads data from various sources '
            print 'and uploads data to a data bank.'
            print 'Filtering and archiving is done using "cleanup".'
            print '-------------------------------------'
            print 'Usage:'
            print 'collectfile.py -c <creddb> -e <credtransfer> -l <localpath> -r <remotepath> -p <protocol> -s <sensorid> -t <stationid> -b <startdate> -d <depth> -a <dateformat> -f <filefomat> -g <flag> -o <disableproxy=True> -w <walk=True> -u <user> -x <uppercase> -m <insert-table> -z <zip>'
            print '-------------------------------------'
            print 'Options:'
            print '-c (required) : provide the shortcut to the data bank credentials'
            print '-e            : credentials for transfer protocol'
            print '-l            : localpath - if provided, raw data will be stored there'
            print '-r (required) : remotepath - path to the data to be collected'
            print '-p            : protocol of data access - required for ftp and scp'
            print '-s            : ID of the sensor (required if not contained in the data'
            print '                meta information)'
            print '-t            : ID of the station i.e. the Observatory code (required if'
            print '                not in meta data)'
            print '-b            : date to start with, like 2014-11-22, default is current day'
            print '-d            : depth: 1 means today, 2 today and yesterday, 3 last three days, etc'
            print '-a            : dateformat in files to be read'
            print '                like "%Y-%m-%d" for 2014-02-01'
            print '                     "%Y%m%d" for 20140201'
            print '                Check out pythons datetime function for more info'
            print '-f            : fileformat of data file to be read.' 
            print '                Add %s as placeholder for date'     
            print '                examples: "WIC_%s.bin"'
            print '                          "Mydata-%s.min"'
            print '                          "WIC_%s.*" -> asterix probably bot working --- TODO'
            print '                          "WIC_2013.all" - no dateformat -> single file will be read'
            print '-g (no input) : read flaglist from DB if db is opened and add flags'
            print '-o (no input) : if selected any systems proxy settings are disabled'
            print '-w (no input) : if selected all subdirectories below remote path will be searched for'
            print '                filename pattern. Only works for local directories and scp.'     
            print '-u            : perform upload as this user - necessary for cron and other root jobs'
            print '                as root cannot use scp transfer.'     
            print '-x            : use uppercase for dateformat (e.g. NOV2014 instead of Nov2014)'
            print '-m            : force data to the given table name.' 
            print '-z            : if option l is selected raw data will be zipped within localpath.' 
            print '-------------------------------------'
            print 'Examples:'
            print 'python collectfile.py -c cobsdb -e gdas -p ftp -r "/data/archive/"' 
            print '      -s POS1_N432_0001 -t WIC -a "%Y%m%d" -f "*%s.bin" -o '
            print 'python collectfile.py -c cobsdb -r "/srv/data/"' 
            print '      -s LEMI036_1_0001 -t WIC -a "%Y-%m-%d" -f "LEMI036_1_0001_%s.bin" '
            print 'python collectfile.py -c cobsdb -r "/media/Samsung/Observatory/archive/WIK/DIDD_3121331_0002/DIDD_3121331_0002_0001/" -s DIDD_3121331_0002 -t WIK -b "2012-06-01" -d 30 -a "%Y-%m-%d" -f "DIDD_3121331_0002_0001_%s.cdf" -g -l "/srv/archive"'

            sys.exit()
        elif opt in ("-c", "--creddb"):
            creddb = arg
        elif opt in ("-e", "--credtransfer"):
            credtransfer = arg
        elif opt in ("-l", "--localpath"):
            localpath = arg
        elif opt in ("-p", "--protocol"):
            protocol = arg
        elif opt in ("-r", "--remotepath"):
            remotepath = arg
        elif opt in ("-s", "--sensorid"):
            sensorid = arg
        elif opt in ("-t", "--stationid"):
            stationid = arg
        elif opt in ("-d", "--depth"):
            try:
                depth = int(arg)
                if not depth >= 1:
                    print "depth needs to be positve" 
                    sys.exit()
            except:
                print "depth needs to be an integer" 
                sys.exit()
        elif opt in ("-a", "--dateformat"):
            dateformat = arg
        elif opt in ("-b", "--begin"):
            startdate = arg
        elif opt in ("-f", "--fileformat"):
            fileformat = arg
        elif opt in ("-o", "--option"):
            disableproxy=True
        elif opt in ("-g", "--flag"):
            flagging=True
        elif opt in ("-w", "--walk"):
            walk=True
        elif opt in ("-u", "--user"):
            defaultuser = arg
        elif opt in ("-x", "--uppercase"):
            uppercase=True
        elif opt in ("-i", "--insert-table"):
            inserttable = arg
        elif opt in ("-z", "--zip"):
            zipping=True

    if localpath == '' and creddb == '':
        print 'Specify either a shortcut to the credential information of the database or a local path:'
        print '-- check collectfile.py -h for more options and requirements'
        sys.exit()
    if fileformat == '':
        print 'Specify a fileformat: -f myformat.dat !'
        print '-- check collectfile.py -h for more options and requirements'
        sys.exit()
    if "%s" in fileformat and dateformat == '':
        print 'Specify a dateformat for placeholder in fileformat!'
        print '-- check collectfile.py -h for more options and requirements'
        sys.exit()
    if walk:
        if not protocol == '' and not protocol == 'scp': 
            print ' Walk mode only works for local directories and scp access.'
            print ' Switching walk mode off.'
            walk = False
    if credtransfer == '':
        user = ''
        password = ''
        address = ''
    else:
        user=mpcred.lc(credtransfer,'user')
        password=mpcred.lc(credtransfer,'passwd')
        address = mpcred.lc(credtransfer,'address')
 
    if not creddb == '':
        print "Accessing data bank ..."
        try:
            db = MySQLdb.connect (host=mpcred.lc(creddb,'host'),user=mpcred.lc(creddb,'user'),passwd=mpcred.lc(creddb,'passwd'),db =mpcred.lc(creddb,'db'))
            print "success"
        except:
            print "failure - check your credentials"
            sys.exit()

    # loaded all credential (if started from root rootpermissions are relquired for that)
    # now switch user for scp
    if not defaultuser == '':
        uid=pwd.getpwnam(defaultuser)[2]
        os.setuid(uid)
    
    datelist = []
    if startdate == '':
        current = datetime.utcnow() # make that a variable
    else:
        current = DataStream()._testtime(startdate)

    newcurrent = current
    for elem in range(depth):
        if not dateformat == '':
            if dateformat == '%b%d%y': #exception for MAGREC
                newdate = datetime.strftime(newcurrent,dateformat)
                datelist.append(newdate.upper())
            else:
                datelist.append(datetime.strftime(newcurrent,dateformat))
            newcurrent = current-timedelta(days=elem+1)
        else:
            datelist = ['dummy']

    print "Dealing with time range:", datelist
    #user = 'cobs'
    #address =  '138.22.188.207'
    #transferpath =  '/home/data/rcs/sgo-radon/RCS-T7-2016-01-13_00-00-00.txt'
    #tmppath = '/tmp'
    #password =  '8ung2rad'

    #scptransfer(user+'@'+address+':'+transferpath,tmppath,password)
    try:
        path = ''
        if not protocol == '':
            path += protocol + "://"
        if not user == '' and not password=='':
            path += user + ":" + password + "@"
        if not address == '':
            path += address
        if not remotepath == '': ### Expected issue with windows.......
            if not remotepath.endswith('/'):
                remotepath += '/'
            path += remotepath

        initial_remotepath = remotepath
        for date in datelist:
            #if uppercase:
            #    date = date.upper()
            if "%s" in fileformat:
                filename = fileformat % date
            else:
                filename = fileformat
            # get a file list if walk mode is selected
            remotepath = initial_remotepath
            filelist = []
            if walk:
                if protocol == 'scp':
                    filelist = ssh_remotefilelist(remotepath, date, user,address,password)
                    filelist = [elem for elem in filelist if not elem == '' and not elem == ' ']
                    remotepath = ''
                elif protocol == '':
                    tmplist = walkdir(filename,remotepath)
                    filelist = [elem.replace(remotepath,'') for elem in tmplist]
                    if len(filelist) < 1:
                        print "No data found matching the selected file pattern"
                        pass 
            else:
                filelist.append(filename)

            print "Uploading the following data set(s):"
            for elem in filelist:
                print " - ", elem

            for filename in filelist:
                tmppath = ''
                tmpname = ''
                filepath = os.path.join(path, filename)
                if protocol == 'scp':
                    # get data by scp transfer and save in /tmp ## what about windows???
                    print "Starting SCP access ..."
                    if not user =='' and not address == '' and not password == '':
                        if filename.startswith('/'):
                            sp = os.path.split(filename)
                            remotepath = sp[0]
                            filetmpname = sp[1]
                        else:
                            filetmpname = filename
                        tmppath = '/tmp' ### change that to localpath if provided e.g. /srv/archive/ -> add subdirs stationID/SensorID/raw
                        tmpname = os.path.join(tmppath,filetmpname)
                        transferpath = os.path.join(remotepath,filetmpname)
                        if not os.path.exists(tmppath):
                            os.makedirs(tmppath)
                        #print user, address, transferpath,tmppath,password
                        scptransfer(user+'@'+address+':'+transferpath,tmppath,password,timeout=60)
                        #print "Data received ..."
                        # add date to a log file for later repetition for failed scp
                        filepath = tmpname
                        #print "Data received ..."
                    else:
                        print "Insufficient data for scp access"

                #print path
                #path = "/srv/data/LEMI036_1_0001_2013-09-21.bin"
                #path='ftp://sdas:sdas2000@138.22.188.18/data/archive/WIC_v1_min_%s.bin' % dayf
                try:
                    data = read(filepath,disableproxy=disableproxy)

                    try:
                        test = data.header['StationID']
                        if not stationid == '':
                            data.header['StationID'] = stationid
                            print "StationID changed to:", data.header['StationID']
                    except:
                        if not stationid == '':
                            data.header['StationID'] = stationid
                        else:
                            print "Could not find station ID in datafile"
                            print "Please provide by using -t stationid"
                            sys.exit()
                    print "Using StationID", data.header['StationID']
                    try:
                        test = data.header['SensorID']
                        if not sensorid == '':
                            data.header['SensorID'] = sensorid
                            print "SensorID changed to:", data.header['SensorID']
                    except:
                        if not sensorid == '':
                            data.header['SensorID'] = sensorid
                        else:
                            print "Could not find sensor ID in datafile"
                            print "Please provide by using -s sensorid"
                            sys.exit()
                    
                    if not localpath == '':
                        sensid = data.header['SensorID']
                        # One Wire treatment for correct path: 
                        if sensid.endswith('0000') and not '_' in sensid:
                            sensid = sensid+'_0001'
                        rawpath = os.path.join(localpath,stationid,sensid,'raw')
                        if not os.path.exists(rawpath):
                            os.makedirs(rawpath)
                        if tmpname == '':
                            print "No data downloaded (local or ftp access) - writing cdf coded data as raw"
                            data.write(rawpath,filenamebegins=sensid,format_type='PYCDF')
                        elif '*' in tmpname:
                            for truefile in glob(tmpname):
                                shutil.copy(truefile, rawpath) ## copy avoids overwrite problems
                                if zipping:
                                    oldname = os.path.basename(truename)
                                    zipname = oldname+'.zip'
                                    oldpath = os.path.join(rawpath,oldname)
                                    with zipfile.ZipFile(os.path.join(rawpath,zipname), 'w') as myzip:
                                        myzip.write(oldpath,os.path.basename(oldpath), zipfile.ZIP_DEFLATED)
                                    os.remove(oldpath)
                        else:
                            shutil.copy(tmpname, rawpath)
                            if zipping:
                                oldname = os.path.basename(tmpname)
                                zipname = oldname+'.zip'
                                oldpath = os.path.join(rawpath,oldname)
                                with zipfile.ZipFile(os.path.join(rawpath,zipname), 'w') as myzip:
                                    myzip.write(oldpath,os.path.basename(oldpath), zipfile.ZIP_DEFLATED)
                                os.remove(oldpath)
                    if not tmppath == '':
                        if '*' in tmpname:
                            for truefile in glob(tmpname):
                                os.remove(truefile)
                        else:
                            os.remove(tmpname)

                    print "Apply flagging information"
                    if flagging and db:
                        flaglist = db2flaglist(db,sensorid=data.header['SensorID'])
                        if len(flaglist) > 0:
                            for i in range(len(flaglist)):
                                data = data.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])

                        #print "Flaglist:", flaglist
                    print "Adding %s data points to DB now" % str(data.length()[0])
                    if db:
                        if not len(data.ndarray[0]) > 0:
                            data = data.linestruct2ndarray()
                        writeDB(db,data)
                        #if inserttable == '':
                        #    stream2db(db,data,mode='replace')
                        #else:
                        #    stream2db(db,data,mode='force',tablename=inserttable)
                    #if not localpath == '':
                    #    if os.path.isdir(localpath): ##  check that 
                    #        data.write(localpath,filenamebegins=sensorid+'_',format_type='PYBIN')
                    #    else:
                    #        print "Directory %s does not exist - aborting" % localpath
                    #        sys.exit()
                except:
                    print "Data not found or not readable"
                    print "Proceeding with next date..."
                    pass

    except:
        print "Unkown error while writing to data bank"
        sys.exit()

if __name__ == "__main__":
   main(sys.argv[1:])



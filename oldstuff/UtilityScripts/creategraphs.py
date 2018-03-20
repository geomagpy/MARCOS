#!/usr/bin/env python
"""
MagPy - Create graphs from data bank contents and distribute them 
"""

from magpy.stream import *
from magpy.database import *
import magpy.mpplot as mp
from magpy.opt import cred as cr

import getopt
import fnmatch
import pwd


'''
Changelog:
2014-11-06:   RL added this function.
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
    walk=False
    flaglist = []
    defaultuser = ''
    uppercase=False

    try:
        opts, args = getopt.getopt(argv,"hc:t:l:k:a:r:p:b:e:o:",["creddb=","tablelist=","pathlist=","keylist=","credtransfer=","remoteaddress=","protocol=","begin=","end=","options=",])
    except getopt.GetoptError:
        print 'creategraphs.py -c <creddb> -t <tablelist> -l <pathlist> -k <keylists>  -a <credtransfer> -r <remoteaddress> -p <protocol> -b <begin> -e <end> -o <optiondict>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '-------------------------------------'
            print 'Description:'
            print 'creategraphs.py reads data from various sources '
            print 'and creates plots.'
            print 'These can also be send directly to any host.'
            print '-------------------------------------'
            print 'Usage:'
            print 'creategraphs.py -c <creddb> -t <tablelist> -l <pathlist> -k <keylists> -a <credtransfer> -r <remoteaddress> -p <protocol> -b <begin> -e <end> -o <optiondict>'
            print '-------------------------------------'
            print 'Options:'
            print '-c            : provide a shortcut to the data bank credentials'
            print '-t            : credentials for transfer protocol'
            print '-l            : pathlist - if provided data will be taken from here and not from database'
            print '-r            : remoteaddress - path/url/etc to which graphs are stored/send'
            print '                Overrides the credential path given by e'
            print '-p            : protocol of sending graphs - required for ftp and scp'
            print '-t            : tablelist - data tables which contain the information to be plotted'
            print '                e.g. DATA1_0001_0001, DATA2_0001_0001'
            print '-k            : keylists - which data is plotted'
            print '                e.g. (x,y,z,t1),(f)'
            print '-b            : date to start with, like 2014-11-22, default is current day'
            print '-e            : date to end with'
            print '-o            : Options:'
            print '                Will be added below...'
            print '                     "%Y%m%d" for 20140201'
            print '                Check out pythons datetime function for more info'
            print '                fileformat of data file to be read.' 
            print '                Add %s as placeholder for date'     
            print '                examples: "WIC_%s.bin"'
            print '                          "Mydata-%s.min"'
            print '                          "WIC_%s.*" -> asterix probably bot working --- TODO'
            print '                          "WIC_2013.all" - no dateformat -> single file will be read'
            print '-------------------------------------'
            print 'Examples:'
            print 'python collectfile.py -c cobsdb -e gdas -p ftp -r "/data/archive/"' 
            print '      -s POS1_N432_0001 -t WIC -a "%Y%m%d" -f "*%s.bin" -o '
            print 'python collectfile.py -c cobsdb -r "/srv/data/"' 
            print '      -s LEMI036_1_0001 -t WIC -a "%Y-%m-%d" -f "LEMI036_1_0001_%s.bin" '
            print 'python collectfile.py -c cobsdb -r "/media/Samsung/Observatory/archive/WIK/DIDD_3121331_0002/DIDD_3121331_0002_0001/" -s DIDD_3121331_0002 -t WIK -b "2012-06-01" -d 30 -a "%Y-%m-%d" -f "DIDD_3121331_0002_0001_%s.cdf" -g'

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
        user=cr.lc(credtransfer,'user')
        password=cr.lc(credtransfer,'passwd')
        address = cr.lc(credtransfer,'address')
 
    if not creddb == '':
        print "Accessing data bank ..."
        try:
            db = mysql.connect (host=cr.lc(creddb,'host'),user=cr.lc(creddb,'user'),passwd=cr.lc(creddb,'passwd'),db =cr.lc(creddb,'db'))
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
        for date in datelist:

            #if uppercase:
            #    date = date.upper()
            if "%s" in fileformat:
                filename = fileformat % date
            else:
                filename = fileformat
            # get a file list if walk mode is selected
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
                    if not user =='' and not address == '' and not password == '':
                        if filename.startswith('/'):
                            sp = os.path.split(filename)
                            remotepath = sp[0]
                            filetmpname = sp[1]
                        else:
                            filetmpname = filename
                        tmppath = '/tmp'
                        tmpname = os.path.join(tmppath,filetmpname)
                        transferpath = os.path.join(remotepath,filetmpname)
                        if not os.path.exists(tmppath):
                            os.makedirs(tmppath)
                        scptransfer(user+'@'+address+':'+transferpath,tmppath,password)
                        # add date to a log file for later repetition for failed scp
                        filepath = tmpname
                    else:
                        print "Insufficient data for scp access"

                #print path
                #path = "/srv/data/LEMI036_1_0001_2013-09-21.bin"
                #path='ftp://sdas:sdas2000@138.22.188.18/data/archive/WIC_v1_min_%s.bin' % dayf
                try:
                    data = read(filepath,disableproxy=disableproxy)

                    if not tmppath == '':
                        os.remove(tmpname)
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
                    print "Apply flagging information"
                    if flagging and db:
                        flaglist = db2flaglist(db,sensorid=data.header['SensorID'])
                        if len(flaglist) > 0:
                            for i in range(len(flaglist)):
                                data = data.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])
                        #print "Flaglist:", flaglist
                    print "Adding %s data points to DB now" % str(len(data))
                    if db:
                        if inserttable == '':
                            stream2db(db,data,mode='replace')
                        else
                            stream2db(db,data,mode='force',tablename=inserttable)
                    if not localpath == '':
                        if os.path.isdir(localpath): ##  check that 
                            data.write(localpath,filenamebegins=sensorid+'_',format_type='PYBIN')
                        else:
                            print "Directory %s does not exist - aborting" % localpath
                            sys.exit()
                except:
                    print "Data not found or not readable"
                    print "Proceeding with next date..."
                    pass

    except:
        print "Unkown error while writing to data bank"
        sys.exit()

if __name__ == "__main__":
   main(sys.argv[1:])


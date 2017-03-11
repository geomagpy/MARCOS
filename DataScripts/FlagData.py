#!/usr/bin/env python
"""

FlagData.py:

Access data from archive or database and flag it. Creates Flaglist and add it to the database

python FlagData.py -c testdb -p "/media/SamsungArchive/archive/WIC/POS1_N432_0001/raw/*" -b "2015-10-01" -e "2015-11-01" -r

python FlagData.py -c testdb -p "/media/SamsungArchive/archive/WIC/FGE_S0252_0001/raw/*" -b "2013-12-01" -e "2014-02-01" -s FGE_S0252_0001 -r

"""
from __future__ import print_function


#import sys
#sys.path.append('/home/leon/Software/magpy/trunk/src')
#from stream import *
#import mpplot as mp
#from database import *
#from opt import cred as mpcred

from magpy.stream import *
import magpy.mpplot as mp
from magpy.database import *
from magpy.opt import cred as mpcred

import getopt
import fnmatch
import pwd, grp  # for changing ownership of web files


def main(argv):
    creddb = ''				# c
    path = ''				# p
    table = ''   			# t
    sensorid = ''   			# s
    keys = []				# v
    begin = '1900-01-01'		  		  # b
    end = datetime.strftime(datetime.utcnow(),"%Y-%m-%dT%H:%M:%S") # e
    show = False			# l
    outlier = False			# o
    write = False			# w
    remove = False			# r

    try:
        opts, args = getopt.getopt(argv,"hc:t:s:p:b:e:v:wor",["cred=","table=","path=","begin=","end=",])
    except getopt.GetoptError:
        print('FlagData.py -c <creddb> -p <path> -t <table> -o <outlier> -l <list> -v <variables> -s <sensorid> -b <startdate>  -e <enddate> -w <write> -r <remove>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('FlagData.py reads any data from database or files and opens')
            print('them for graphical analysis and flagging.')
            print('It returns flagged data streams and a flaglist,')
            print('stored in the data base if db credentials are provided.')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('FlagData.py -c <creddb> -p <path> -t <table> -s <show> -b <startdate>  -e <enddate> -v <variables> -w <write> -r <remove>')
            print('-------------------------------------')
            print('Options:')
            print('-c            : provide the shortcut to the data bank credentials')
            print('-t            : table name to be openend')
            print('                    or a credential shortcut for a remote connection ')
            print('-l            : list available tables')
            print('-p            : path to data to be opened. Please note: if t and p are provided')
            print('              : then only the table is opened. If p is provided and c not then')
            print('              : flagging information is not stored.')
            print('-b            : startdate - begin of analysis ')
            print('-e            : enddate - default is today ')
            print('-v            : specify variables to be plotted ')
            print('              : e.g. x,y,z,dx,dy,dz ')
            print('-o            : automatically flag outlier ')
            print('-s            : provide a sensor id for flaglist ')
            print('-w            : write data back to selected path/DB ')
            print('              : table is overwritten, pycdf files are created/overwritten in path')
            print('-r            : remove already flagged data - only flaglist will be added to DB.')
            print('              : Option write will be disabled. ')
            print('-------------------------------------')
            print('Examples:')
            print('1. Using database tables:') 
            print('python FlagData.py -c mydatabase -t MYDATAID_00001 ')
            print('      -b 2014-01-01 -e 2014-02-01') 
            print('2. Using it on files:') 
            print('python FlagData.py -c mydatabase -p "/srv/archive/MyData/*" ')
            print('      -b "2014-01-01" -e "2014-02-01"') 
            sys.exit()
        elif opt in ("-c", "--creddb"):
            creddb = arg
        elif opt in ("-p", "--path"):
            path = arg
        elif opt in ("-t", "--table"):
            table=arg
        elif opt in ("-s", "--sensorid"):
            sensorid = arg
        elif opt in ("-b", "--begin"):
            begin = arg
        elif opt in ("-e", "--end"):
            end = arg
        elif opt in ("-v", "--variabes"):
            vlist = []
            try:
                vlist = arg.split(',')
                vlist = [elem for elem in vlist if elem in NUMKEYLIST]
            except:
                try:
                    vlist = [arg]
                    vlist = [elem for elem in vlist if elem in NUMKEYLIST]
                except:
                    vlist = []
            keys = vlist
        elif opt in ("-l", "--list"):
            show = True
        elif opt in ("-o", "--outlier"):
            outlier = True
        elif opt in ("-w", "--write"):
            write = True
        elif opt in ("-r", "--remove"):
            remove = True

    if path == '' and table == '':
        print('Specify either a path or a database table')
        print('-- check FlagData.py -h for more options and requirements')
        sys.exit()

    if creddb == '' and path == '' and not table == '':
        print('Specify database credentials for using tables !')
        print('-- check FlagData.py -h for more options and requirements')
        print('       and MARCOS.README for credentials')
        sys.exit()

    if not creddb == '':
        print("Accessing data bank ...")
        try:
            db = mysql.connect (host=mpcred.lc(creddb,'host'),user=mpcred.lc(creddb,'user'),passwd=mpcred.lc(creddb,'passwd'),db =mpcred.lc(creddb,'db'))
            print("success")
        except:
            print("failure - check your credentials")
            sys.exit()
    else:
        db = False

    if not table == '':
        print("Getting table:", table, begin, end)
        data = readDB(db,table,starttime=begin,endtime=end)
    elif not path == '':
        print("Reading data:", path, begin, end)
        data = read(path,starttime=begin,endtime=end)
        print("Found datapoints", data.length())
    
    if data.length()[0] > 0:
        if sensorid == '':
            try:
                si = data.header['SensorID']
            except:
                si = ''
        else:
            data.header['SensorID'] = sensorid
            si = sensorid
        print("SensorID:", si)
        # flag outlier
        if outlier:
            print("Flagging prominent outliers automatically")
            data = data.flag_outlier()
        # Eventually load existing flag information
        if not creddb == '' and not si == '':
            print("Loading existing flags")
            flaglist = db2flaglist(db,si) #data.header['SensorID'])
            print("Applying flags")
            data = data.flag(flaglist)
        # Eventually removed already flagged data
        if remove:
            print("Removing flags")
            data = data.remove_flagged()
            write = False

        #  plotFlag - eventually extend and save extended flaglist
        print("Plotting")
        if not len(keys) > 0:
            data,newflaglist = mp.plotFlag(data)
        else:
            data,newflaglist = mp.plotFlag(data,variables=keys)
        if not creddb == '':
            flaglist2db(db, newflaglist)

        if write:
            if not table == '':
                writeDB(db,data)
            elif not path == '':
                #data.write(path,filenamebegins=scinst+'_scalar_'+str(year),dateformat='%Y',coverage='all',format_type='PYCDF')
                pass

        data = data.remove_flagged()
        mp.plot(data)

if __name__ == "__main__":
   main(sys.argv[1:])


#!/usr/bin/env python
"""
Setting up a clean new database from raw data 
"""
from magpy.database import *
from magpy.opt import cred as mpcred
import getopt

def main(argv):
    cred = ''
    db = ''
    user = ''
    passwd = ''
    host = ''
    shortcut = ''
    try:
        opts, args = getopt.getopt(argv,"hc:d:u:p:o:",["cred=","database=","user=","password=","host="])
    except getopt.GetoptError:
        print 'setupDB.py -c <credentials> -d <database> -u <user> -p <password> -o <host>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'Usage:'
            print 'setupDB.py -d <database> -u <user> -p <password> -o <host>'
            print 'Please note: all options need to be provided'
            print 'Examples:'
            print 'on a local machine: setupDB.py -d MyDB -u max -p secret -o localhost'
            print 'on remote machines: setupDB.py -d MyDB -u max -p secret -o 1.1.1.1'
            print 'if credential is existing: setupDB.py -c mydbshortcut'
            sys.exit()
        elif opt in ("-c", "--cred"):
            shortcut = arg
        elif opt in ("-d", "--database"):
            db = arg
        elif opt in ("-u", "--user"):
            user = arg
        elif opt in ("-p", "--password"):
            passwd = arg
        elif opt in ("-o", "--host"):
            host = arg

    if cred == '':
        if db == '':
            print 'Specify a database by the -d option:'
            print '-- check setupDB.py -h for more options and requirements'
            sys.exit()
        if user == '':
            print 'Specify a user by the -u option:'
            print '-- check setupDB.py -h for more options and requirements'
            sys.exit()
        if passwd == '':
            print 'Specify a password by the -p option:'
            print '-- check setupDB.py -h for more options and requirements'
            sys.exit()
        if host == '':
            print 'Specify a host by the -t option:'
            print '-- check setupDB.py -h for more options and requirements'
            sys.exit()
        create = True
    else:
        print 'Credential shortcut provided - all other options will be ignored'
        create = False

    if create:
        mpcred.cc('db',db,db=db,user=user,passwd=passwd,host=host)
        print "Added encrypted credentials ... check the magpy cookbook on how to use/access/modify that"
        print "Group: db, Shortcut: %s" % db
        cred = db

    db = MySQLdb.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
    print "Initializing data bank ..."
    dbinit(db)
    print "success"

if __name__ == "__main__":
   main(sys.argv[1:])





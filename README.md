MARCOS - version 0010 (May 2015)
Developers: R. Leonhardt, R. Bailey (ZAMG)

MARCOS = Magpy Automated Remote Collection and Organization System

##########################
MINI TO-DO:
- WebScripts directory
- Nagios directory
##########################

#################################
Version info:
0003 first working version

0004:
* modified data2DB app to support modifications of dbdelete and corrected archiving part
* added di.py for the analysis of absolute measurements for magpy supported formats
* changed collector_moon references to collector-moon because of autostart

0005 (Nov 2014):
* improved collectfile and dataDB routines 

0006 (Nov 2014):
* improved description
* corrected FTP issues and alpha/beta treatment in di.py 

0007 (Feb 2015):
* added monitor.py (a monitoring routine for data base entries, which can be used with 
          nagios to simply monitor the presence of user specified incoming data)
* modified filtering functions in cleanupDB and data2DB -> added don't fill gap as default 
          option for filtering.
          this way individually missing data points don't corrupt filtering
          (does not affect magnetic data, but is necessary for Balances and RCS data) 
* collectfile: corrected the path selection using walk mode- previously only the first data set has been 
          copied correctly - then it stuck within this path
* added upload_data2DB.sh: a small bash script to repeately call data2DB avoiding memory errors

0008 (May 2015):
* added simpleread.py (to download e.g. kp data without storage in a DB)
* modified monitor.py: added a exlude option to select sensors not to be tested.
          Useful for example to monitor data sets with different upload times
          e.g. exclude all data with daily uploads from default process and check them separately * added logrotate script for marcos.log

#####################################################################
          Setup and Structure of Collector Units (MARCOS)
#####################################################################

# -------------------------------------------------------------------
1. Installation requirements
# -------------------------------------------------------------------
	Required packages:
	- Geomagpy >= 0.1.264 (and its requirements)
		python = 2.7.x, matplotlib >= 1.0.0, SciPy, NumPy, python-mysql
                optional: spacepy >= 1.3, netcdf, pexpect,


# -------------------------------------------------------------------
2. Strucure/Files in home directory of MARTAS user
# -------------------------------------------------------------------

All necessary files are found within the MARCOS directory 
	SYSTEMNAME:  			(e.g. RASPBERRYONE, CERES) contains a description of the system 
					and a history of changes made to it
        collector-moon.py:		the main program for data collection of a single 
					moon (please open and modify user specific 
					variables according your requirements)
	README.MARCOS:			You are here.

	DataScripts/cleanupDB.py:	to be run from cron for filtering raw data within databank and  
                                        to remove old entries from the MARCOS db, create archive
                                        (python collectfile.py -h for help)
	DataScripts/collectfile.py:	to be run from cron for collecting datafiles from remote machines
                                        or network directories as well as the MARTAS buffer and append
                                        them to the database.
                                        (python collectfile.py -h for help)
	DataScripts/data2DB.py:	        upload existing data files to the MARCOS data bank
                                        please note: this method also creates filtered tables
                                        and removes old data from the databank
                                        (python data2DB.py -h for help)
	DataScripts/upload_data2DB.sh:  upload many existing data files to the MARCOS data bank
                                        using data2DB. Please modify it to your needs.
                                        (bash upload_data2DB.sh for execute)
	DataScripts/setupDB.py:		initialize an empty mysql database with the MARCOS structure
                                        (setupDB.py -h for help)
	DataScripts/simpleread.py:	simple application of magpy read and write
                                        to be used for downloads and files without DB
                                        (too be edited e.g. nano simpleread.py)

	Logs/marcos.log: 		log file for standard collector_martas jobs. Needs to have 
                                        write permissions for everbody (chmod 666) 
	Logs/verify.log: 		logs buffer verifications 
                                        use ... > ~/MARCOS/Logs/verify.log 2>&1 
                                        to redirect output of collect.sh  
	Logs/restart.log: 		logs restarting attempts (see verify.log)

	MartasFiles/..:		        empty directory which will hold copies of files 
					for database setup
	MartasSensors/..:	        empty directory which will hold copies of sensor 
					lists from the MARTAS

	Nagios/add2nrpe.cfg:		command to check for marcos process for nagios 
                                        (client side, requires nrpe)
	Nagios/add2server.cfg:		service description to add on the cfg file (server side)
	Nagios/monitor.py:		checks for the actuality of specified data within the database
                                        and logs missing data
                                            requires MagPy >= 0.1.296

	UtilityScripts/addcred.py:	add encrypted credentials for secure usage of 
					other scripts (python addcred.py -h for help)
	UtilityScripts/collect.sh:      contains independet calls of collectfile.py to be scheduled
                                        by cron for uploading data records. Recommended also for 
                                        each MARTAS to verify the contents of the real time MARCOS DB. 
	UtilityScripts/collectorrestart.sh:      use crontab to restart each collector job regularly 
	UtilityScripts/marcos.conf:     to be run at boot time using upstart (alternative to martas.sh)
	UtilityScripts/marcos.sh:	to be run at boot time for starting the acquisition

	WebScripts/index.html:		(TODO) html page for displaying data from all available MARTAS.
	                        	Modify and copy to /var/www/ 

	examples/...:			contains some examples for above mentioned files
	

# -------------------------------------------------------------------
3. Setting up the system
# -------------------------------------------------------------------
(please also check the recommended setup in 3.5)

3.1 REQUIRED modifications:
###########################

Please go through all steps in the given order:
(Note: all arguments preceded by a '#' are to be entered by the user.)


I. Setup a mysql database:
    a) Add data bank (MySQL needs to be installed)
        $ mysql -u root -p mysql
        # then add a new database e.g. mydb 
        mysql> CREATE DATABASE #DB-NAME; 
    b) User needs exists which has access and write permissions
        - if not, create one - login as root to mysql: 
        mysql> GRANT ALL PRIVILEGES ON #DB-NAME.* TO '#USERNAME'@'localhost' IDENTIFIED BY '#PASSWORD';

    (optional c) for remote access of the database:
        mysql> GRANT ALL PRIVILEGES ON #DB-NAME.* TO '#USERNAME'@'%' IDENTIFIED BY '#PASSWORD';
        
        modify the mysql config file: (/etc/mysql/my.cfg in Linux systems) 
        ## uncomment #bind-address  127.0.0.1
        to allow external access
        To limit the access you could define ip criteria in iptables - please check the tutorials

II. Add credentials for boot time running:
	$ cd ~/MARCOS/UtilityScripts
	$ sudo python addcred.py -t transfer -c #MARTASNAME -u #USERNAME -p #PASSWORD -a #MARTAS-IP
	# repeat above line for each martas client
	$ sudo python addcred.py -t db -c #DB-NAME -d #DB-NAME -u #DB-USERNAME -p #DB-PASSWORD -o localhost

	# Please also setup all information for the defaultuser as well for normal runtime:
	# (same command without sudo)
	$ python addcred.py -t transfer -c #MARTASNAME -u #USERNAME -p #PASSWORD -a #MARTAS-IP
	# repeat above line for each martas client
	$ python addcred.py -t db -c #DB-NAME -d #DB-NAME -u #DB-USERNAME -p #DB-PASSWORD -o localhost


III. Apply setupDB.py
     This file will initiate the magpy database for you including encrypted credential 
     information to access it later on
     (For help on how to use:	$ python setupDB.py -h)
     From MARCOS directory (please replace the obvious):
     (if you really have no idea what is obvious then - I hate to say that - ask the administrator):
	$ cd ~/MARCOS/DataScripts
	$ python setupDB.py -d #DB-NAME -u #DB-USERNAME -p #DB-PASSWORD -o localhost

     Now open a browser and go to "localhost/phpmyadmin" to check the DB exists!
     (... if phpmyadmin and apache are installed ...
      See following link for details on how to install everything:
      http://www.howtoforge.com/installing-apache2-with-php5-and-mysql-support-on-ubuntu-13.04-lamp)
     
      
IV. Edit MARCOS scripts:
   (assuming you are starting in the MARCOS directory with a MARTAS sensor system called "atlas")

    a) ----- collector-moon.py -------
    ##################################
     Make copy of collector script:
	$ cd ~/MARCOS
	$ cp collector-moon.py collector-atlas.py
     Use your favorite editor to modify collecter-atlas.py, e.g. vi, nano etc
     Looks like:
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #                 do necessary changes below
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # Name of martas
    clientname = 'atlas'
    # IP of martas
    clientip = '192.168.0.101'
    # Path of MARTAS directory on martas machine
    martaspath = '/home/user/MARTAS' 
    .... 
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #                 do necessary changes above
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    b) ----- marcos.conf or marcos.sh -------
    #########################################
	$ cd ~/MARCOS/UtilityScripts
	$ cp marcos.sh marcos-atlas.sh ( or .conf)
	$ nano marcos-atlas.sh (.conf)
    Insert the correct paths to your MARCOS folder
    e.g. change /home/cobs/MARCOS to /home/myuser/MARCOS
    with the correct moon reference:
    e.g. collector-moon.py to collector-atlas.py

    if you are running MARCOS and MARTAS on the same machine
    then please modify ...

V. Connect to the MARTAS by SSH (at least once):
    This is essential to store the key information for ssh connections locally.
    The key information is then used by the automatic script for secure data access.
    If you have not connectedat least one by ssh, obtainig sensor.txt information will fail.


3.2 STARTING the acquisition system
###################################

Important: Each connected MARTAS requires its own startup script
Therefore cp marcos.conf marcos-martas1.conf if you are running several martas.

OPTION 1 - Using a bootscript (e.g. ubuntu)
	$ sudo cp marcos-atlas.sh /etc/init.d/marcos-atlas
	$ sudo chmod 755 /etc/init.d/marcos-atlas
	$ sudo chown root:root /etc/init.d/marcos-atlas
	$ sudo update-rc.d marcos-atlas defaults

To remove:
	$ sudo update-rc.d -f marcos-atlas remove

OPTION 2 - Using startup (e.g. debian, rasbian, ubuntu etc)
	$ sudo cp marcos-atlas.conf /etc/init/marcos-atlas.conf
	$ sudo chmod 755 /etc/init/marcos-atlas.conf
	$ sudo chown root:root /etc/init/marcos-atlas.conf
	$ sudo service marcos-atlas start  (restart, stop) (please note the sleep interval)

To remove:
	$ sudo rm /etc/init/marcos-atlas.conf


3.3 UPLOADING buffer values frequently
######################################

Depending on network connection internet interruptions may occur.
In order to prevent any data loss you can use the following script:
UtilityScripts/collect.sh. This script collects the buffer files from the
MARTAS and compares to the data in the data bank.

For each MARTAS you have to add a call to the collectfile routine. Ideally you provide login, password and address of each MARTAS using the credential function.

           #!bin/sh
           python /home/mydir/MARCOS/DataScripts/collectfile.py -c #DB-NAME -e #MARTASNAME1 -p scp -r "/srv/ws/atlas/" -t #STATIONCODE -a "%Y-%m-%d" -f "%s.bin" -w -u #USER
           python /home/mydir/MARCOS/DataScripts/collectfile.py -c #DB-NAME -e #MARTASNAME2 -p scp -r "/srv/ws/quaoar/" -t #STATIONCODE -a "%Y-%m-%d" -f "%s.bin" -w -u #USER

Do the required changes. If there is more than one MARTAS, just add in sequence...

Make the file executable by chmod 755:
	$ sudo chmod 755 collect.sh

Add a cronjob / scheduler task:
On Linux:
	$ crontab -e
Add this line (don't forget to modify the path):
	10 0 * * * sh /home/myuser/MARCOS/UtilityScripts/collect.sh
 

3.4 OPTIONAL modifications
##########################

Edit the Utility scripts (cleanup and logfile applications) according to your needs. Use cron to schedule them.

a) Upload old data to databank:
    - use data2DB.py in DataScripts
    (For instructions: $ python data2DB.py -h)
    e.g. python data2DB.py -c cobsdb -p "/media/DAE2-4808/archive/WIC/FGE_S0252_0001/raw/*.sec" -s FGE_S0252_0001 -t WIC -b 2014-08-21 -e 2014-08-29 -a "/media/DAE2-4808/archive"

b) Save some sensitive information for data transfer and database access encrypted etc.:
    - use addcred.py in UtilityScripts
    (For instructions: $ python addcred.py -h)

c) Create archive files
    - cleanupDB.py filters data and creates archive files with all DB information.
    - Set up cleanDB.py and add to crontab:
        # Run it once from bash:
	$ cd ~/MARCOS/DataScripts
	$ python cleanupDB.py
	# Then cron it. If you used "sudo" set the permission back to your defaultuser
	$ crontab -e
	# Add the line:
        20  0  *  *  * python /home/myuser/MARCOS/DataScripts/cleanupDB.py -c #DB-NAME -p /srv/archive
        # to run the job every day 20 minutes past midnight
	# The default user needs write permission or ownership:
        $ sudo chown -R defaultuser:defaultuser /srv/archive/

d) Add non-MARTAS systems by using file upload to DB:
    - collectfile.py gets files from a remote location and adds them directly into the data bank.
	$ cd ~/MARCOS/DataScripts
	# For instructions: $ python collectfile.py -h
	# Then add to crontab...

e) Get a different data format out of the raw files / data bank
    - Use MagPy read(data/databank) and write(format=newformat) functions.


3.5 RECOMMENDED setup
#####################

Assuming you have two MARTAS ('atlas' with IP 192.168.0.101 and 'quaoar' with IP 192.168.0.102)
and a remote server storing data and accessible by normal ftp ('ftp://ftpuser:ftppasswd@10.0.0.1/mydata')
with filename like MyData20141122v.min. You know all essential sensor information and can provide a unique ID for all sensors. You have a stationcode "MyCode" to apply. Your defaultuser on the MARCOS PC is "obs". You are working on a Linux machine with UTC timing.

a) All steps in 3.1 have to be done. Your databank credential shortcut is mydb.
    You now have two collector files in the MARCOS directory:
        collector-atlas.py
        collector-quaoar.py
    And you also have two startup scripts marcos_atlas.conf and marcos_quaoar.conf
b) Start acquisition:
    for .sh (linux - recommended):
    sudo /etc/init.d/marcos-atlas start 
    sudo /etc/init.d/marcos-quaoar start
c) Create some additional credential information for upload and ftp access:
        $ cd ~/MARCOS/UtilityScripts
        $ python addcred.py -t transfer -c ftp -u ftpuser -p ftppasswd -a 10.0.0.1 -l 21
        $ python addcred.py -t transfer -c martas -u scpuser -p scppasswd -a ip_of_martas
d) If you have non-MARTAS file acquisition system: Start routine upload 
   of data from ftp server (every 5 minutes):
    backup old collect.sh:
        $ cp collect.sh collect.bak
    edit collect.sh (should look like):
           #!bin/sh
           python /home/myuser/MARCOS/DataScripts/collectfile.py -c mydb -e ftp -p ftp -r "/mydata/" -t MyCode -a "%Y%m%d" -f "MyData%sv.min" -u obs
    save it...
    make it executable:
        $ chmod 755 collect.sh
    
    add the following line to crontab:
        $ crontab -e
           add:
           */5  *  *  *  * sh /home/myuser/MARCOS/UtilityScripts/collect.sh

e) update data base information for each DATAINFO and SENSOR 

f) Start databank verification with buffer memory of MARTAS once a day:
    get a copy of collect.sh's backup 
        $ cd ~/MARCOS/UtilityScripts
        $ cp collect.bak collectmartas.sh
    edit collectmartas.sh (should look like):
           #!bin/sh
           python /home/myuser/MARCOS/DataScripts/collectfile.py -c mydb -e martas -p scp -r "/srv/ws/atlas/" -t MyCode -a "%Y-%m-%d" -f "%s.bin" -w -u obs
           python /home/myuser/MARCOS/DataScripts/collectfile.py -c mydb -e martas -p scp -r "/srv/ws/quaoar/" -t MyCode -a "%Y-%m-%d" -f "%s.bin" -w -u obs
    save it...
    make it executable:
        $ chmod 755 collectmartas.sh
    
    add the following line to crontab for executing it 10 min past midnight:
        $ crontab -e
        add:
        20  0  *  *  * sh /home/myuser/MARCOS/UtilityScripts/collectmartas.sh
    
g) setup cleanup and archive functions:
    start a initial cleanup
        $ sudo chown -R obs:obs /srv/archive/
	$ cd ~/MARCOS/DataScripts
        $ python cleanupDB.py -c mydb -p /srv/archive

    add the following line to crontab for executing it 15 min past midnight (after verification):
        $ crontab -e
        add:
        30  0  *  *  * python /home/myuser/MARCOS/DataScripts/cleanupDB.py -c mydb -p /srv/archive

h) add cronjob for restarting collector scripts once a day (this way, new MARTAS 
   configurations are automatically registered)
        $ cd ~/MARCOS/UtilityScripts
        edit collectorrestart.sh
        add for each collector:
        #!bin/sh
        /etc/init.d/marcos-martas restart
        $ crontab -e
        add:
        18  0  *  *  * sh /home/myuser/MARCOS/UtilityScripts/collectorrestart.sh
        Please note: restart is performed shortly before verification and buffer upload

   At the end your Crontab should look like:
   # My Scripts for MARCOS
   18  0  *  *  * sh /home/obs/MARCOS/UtilityScripts/collectorrestart.sh
   20  0  *  *  * sh /home/obs/MARCOS/UtilityScripts/collect-mymartas.sh
   30  0  *  *  * sh /home/obs/MARCOS/UtilityScripts/archive.sh 
                        
                           (archive.sh contains the python ... line of e) )


i) modify and extend the data bank's meta information (please do not touch ID's sampling rates and
   other infos directly provided by data files i.e. any at this stage already filled in value)

j) Upload any already existing data sets to the database:
    MARCOS is now running for all current data. Your data base looks fine and contains 
    correct infos. Time to add old measurements... 
        $ cd ~/MARCOS/DataScripts    
        $ python data2DB.py -c 
        e.g. 
        $ python /home/cobs/MARCOS/DataScripts/data2DB.py -c cobs 
               -p "/mnt/magnetik/dIdD-System/*.WIK" -a /srv/archive 
               -s DIDD_3121331_0002 -t WIK -b 2014-06-01 -e 2014-11-11 
               -i 1000 -u -m DIDD_3121331_0002_0001

k) adding di support:
    please note that you need to upload full di analyses with variometer and scalar data first, otherwise the data bank table will be incomplete and any later upload of di values will fail with missing 'dx' messages in the magpy.log

l) Activate logrotation
    - edit /MARCOS/Logs/marcos (check logrotate WIKI)
    - do (on ubuntu and most other Linux versions):
        sudo cp marcos /etc/logrotate.d/
        sudo chmod 644 /etc/logrotate.d/marcos
        sudo chown root:root /etc/logrotate.d/marcos


# ---------------------------------------------------------------------------
4. Customizing the WEB interface of the MARCOS client
# ---------------------------------------------------------------------------

Unlike MARTAS, MARCOS does not start its own Webserver
To easily access and view all connected MARTAS and their provided data, 
three Web based interfaces are recommended:
    - WebScripts/index.html (real-time data viewer) 
	(provided by the MARCOS development team)
	Edit the index.html file by providing a list of MARTAS (name and ip-numbers)

    - phpmyadmin (for direct data base access)
	Open source software - please ask google for details.

    - Full joomla site with php scripts for DB access and viewing
	(contact the MARCOS development team)


# ---------------------------------------------------------------------------
5. Some useful MySQL commands for modifying the database
# ---------------------------------------------------------------------------

# Start MySQL
$ mysql -u USER -p YOURDATABASENAME

# Overview over all tables
> SHOW TABLES; 

# Show Last record of a Data table (e.g. DACF54010000_0001_0001)
> SELECT * from DACF54010000_0001_0001 ORDER BY time DESC LIMIT 1;

# Delete a row from a table
> DELETE FROM DATAINFO WHERE DataID="KERN410_5703742_0001_0005";

# Drop a complete table
> DROP TABLE KERN410_5703742_0001_0005;

# Add values to an existing row of a specific Table
> UPDATE SENSORS SET SensorName="GSM90", SensorGroup="magnetism", SensorType="Overhauzer", SensorDataLogger="GSM90", SensorDataLoggerSerNum="1114800", SensorDataLoggerRevision="0002", SensorDataLoggerRevisionComment="Repaired and calibrated November 2014", SensorDescription="GEM: Overhauzer sensor without GPS", SensorModule="Serial", SensorDate="2011-11-15", SensorRevisionComment="Repaired and calibrated November 2014", SensorRevisionDate="2014-12-01" WHERE SensorID="GSM90_14245_0002";

# Add new data 
> INSERT INTO FLAGS (SensorID,FlagBeginTime,FlagEndTime,FlagComponents,FlagNum,FlagReason,ModificationDate) VALUES ("POS1_N432_0001","2014-09-16 08:30:00.000000","2014-09-16 09:30:00.000000","f","0","Maintenance work at emergency light - DC currents","2015-02-18 12:00:00.000000")


# ---------------------------------------------------------------------------
6. For those who read to the end before doing any changes
# ---------------------------------------------------------------------------

Just modify the code below and copy it to a terminal window you marcos homedirectory to make all necessary parameter changes in all files. 

# Would be nice, wouldn't it
# TODO: write a small install script which sets paths and names correctly




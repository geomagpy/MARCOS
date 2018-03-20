#!/bin/sh


### Uploading files to the databank
### ###############################

#(OK)## Get all current data from a MARTAS client called atlas below folder /srv/ws/ (using scp) 
# python /home/myuser/MARCOS/DataScripts/collectfile.py -c cobsdb -e rasp -p scp -r "/srv/ws/" -t WIC -a "%Y-%m-%d" -f "*%s.bin" -w -u 'defaultuser'

### Get data from a password protected ftp site 
###  add credentials and address first by addcred.py
# python /home/myuser/MARCOS/DataScripts/collectfile.py -c cobsdb -e gdas -p ftp -r "/data/archive/" -s POS1_N432_0001 -t WIC -a "%Y%m%d" -f "WIC_%s.bin" -o

### Get data from a local directory 
#python /home/cobs/MARCOS/DataScripts/collectfile.py -c myhome -r "/srv/ws/europa"  -t MyHome -a "%Y-%m-%d" -w -f "*%s.bin"

#(OK)## Get all current data with similar file pattern in any subfolder below /srv/data/ 
# python /home/myuser/MARCOS/DataScripts/collectfile.py -c cobsdb -r "/srv/data/" -t WIC -a "%Y-%m-%d" -f "*%s*" -w

### Get data from a html site 
# python /home/myuser/MARCOS/DataScripts/collectfile.py -c cobsdb -r "/srv/data/" -s LEMI036_1_0001 -t WIC -a "%Y-%m-%d" -f "LEMI036_1_0001_%s.bin"

### Get data from an open ftp site 
# python /home/myuser/MARCOS/DataScripts/collectfile.py -c cobsdb -r "/srv/data/" -s LEMI036_1_0001 -t WIC -a "%Y-%m-%d" -f "LEMI036_1_0001_%s.bin"

#python /home/myuser/MARCOS/DataScripts/collectfile.py -c myhome -e europa -p scp -r "/srv/ws/europa/" -t MyHome -a "%Y-%m-%d" -f "%s.bin" -w -u cobs

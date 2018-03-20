#!/usr/bin/env python
#********************************************************************
# Simple magpy read functions
#
# Use this script for basic reading options without DB functionality
# Examples: read kp values and store them locally
#
# Application: add to crontab
#	$ crontab -e
#	24 2,5,8,11,14,17,20,23 * * * python /home/cobs/CronScripts/kpdownload/gfzkp_download.py
#	(Job runs every three hours.)
#
#********************************************************************

from __future__ import print_function
from magpy.stream import *
from magpy.transfer import *

kppath = '/srv/archive/external/gfz/kp'

# READ GFZ KP DATA:
# -----------------
kp = read(path_or_url='http://www-app3.gfz-potsdam.de/kp_index/qlyymm.tab')

# Append that data to local list:
kp.write(kppath,filenamebegins='gfzkp',format_type='PYCDF',dateformat='%Y%m',coverage='month')

print("File written successfully.")



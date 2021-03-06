#!/usr/bin/env python
"""
MQTT collector routine of MARCOS: 
MQTT protocol to be used in the Conrad Observatory.
written by by Roman Leonhardt
 
How should it work:
PURPOSE:
collector_mqtt.py subscribes to published data from MQTT clients.

REQUIREMENTS:
1.) install a MQTT broker (e.g. ubuntu: sudo apt-get install mosquitto mosquitto-clients)
2.) Secure comm and authencation: https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

METHODS:
collector.py contains the following methods:

GetSensors: read a local definition file (sensors.txt) which contains information
            on SensorID, Port, Bausrate (better Serial communication details), active/passive, 
            init requirements, optional SensorDesc

GetDefaults: read initialization file with local paths, publishing server, ports, etc.

SendInit: send eventually necessary initialization data as defined in sensors.txt

GetActive: Continuously obtain serial data from instrument and convert it to an binary 
           information line to be published (using libraries)

GetPassive: Send scheduled request to serial port to obtain serial data from instrument 
            and convert it to an binary information line to be published (using libraries)

Usage:
python colector_mqtt.py -x -y -z

"""

from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

## Import MagPy
## -----------------------------------------------------------

local = True
if local:
    import sys
    sys.path.insert(1,'/home/leon/Software/magpy-git/')

from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, subtractStreams
from magpy.database import mysql,writeDB
from magpy.opt import cred as mpcred

## Import Twisted for websocket and logging functionality
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File
from twisted.internet import reactor

import threading
from multiprocessing import Process
import struct
from datetime import datetime 
from matplotlib.dates import date2num, num2date
import numpy as np
import json

# For file export
import StringIO
from magpy.acquisition import acquisitionsupport as acs

## Import MQTT
## -----------------------------------------------------------
import paho.mqtt.client as mqtt
import sys, getopt, os

# Some global variables
global identifier
identifier = {}
streamdict = {}
stream = DataStream()
st = []
senslst = []
headdict = {} # store headerlines for file
headstream = {}
global counter  # use for diffcalc
counter = 0

verifiedlocation = False
destination = 'stdout'
location = '/tmp'
credentials = 'cred'
stationid = 'WIC'
webpath = './web'
webport = 8080
socketport = 5000

## Import WebsocketServer
## -----------------------------------------------------------
def wsThread(wsserver):
    wsserver.set_fn_new_client(new_wsclient)
    wsserver.set_fn_message_received(message_received)
    wsserver.run_forever()

# TODO: find a way how to use these two functions:
def new_wsclient(ws_client,server):
    pass
    # for debug: see which threads are running:
    #print(str(threading.enumerate()))
def message_received(ws_client,server,message):
    pass

ws_available = True
try:
    # available since 0.3.99
    from magpy.collector.websocket_server import WebsocketServer
except:
    ws_available = False

if ws_available:
    global wsserver

def webProcess(webpath,webport):
    """
    These few lines will be started as an own process.
    When the main process is killed, also this child process is killed
    because of having it started as a daemon
    """
    resource = File(webpath)
    factory = Site(resource)
    #endpoint = endpoints.TCP4ServerEndpoint(reactor, 8888)
    #endpoint.listen(factory)
    reactor.listenTCP(webport,factory)
    reactor.run()

def connectclient(broker='localhost', port=1883, timeout=60, credentials='', user='', password=''):
        """
    connectclient method
    used to connect to a specific client as defined by the input variables
    eventually add multiple client -> {"clients":[{"broker":"192.168.178.42","port":"1883"}]} # json type
                import json
                altbro = json.loads(altbrocker)
        """
        client = mqtt.Client()
        # Authentication part
        if not credentials in ['','-']:
            # use user and pwd from credential data if not yet set 
            if user in ['',None,'None','-']: 
                user = mpcred.lc(credentials,'user')
            if password  in ['','-']:
                password = mpcred.lc(credentials,'passwd')
        if not user in ['',None,'None','-']: 
            #client.tls_set(tlspath)  # check http://www.steves-internet-guide.com/mosquitto-tls/
            client.username_pw_set(user, password=password)  # defined on broker by mosquitto_passwd -c passwordfile user
        client.on_connect = on_connect
        # on message needs: stationid, destination, location
        client.on_message = on_message
        client.connect(broker, port, timeout)
        return client


def analyse_meta(header,sensorid):
    """
    source:mqtt:
    Interprete header information
    """
    header = header.decode('utf-8')
    
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    h_elem = header.strip().split()
    if not h_elem[-2].startswith('<'): # e.g. LEMI
        packstr = '<'+h_elem[-2]+'B'
    else:
        packstr = h_elem[-2]
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        log.msg("Different sensorids in publish address {} and header {} - please check - aborting".format(sensorid,si))
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        log.msg("Packing code: {}".format(packstr))
        log.msg("keylist: {}".format(keylist))
    identifier[sensorid+':packingcode'] = packstr
    identifier[sensorid+':keylist'] = keylist
    identifier[sensorid+':elemlist'] = elemlist
    identifier[sensorid+':unitlist'] = unitlist
    identifier[sensorid+':multilist'] = multilist

def create_head_dict(header,sensorid):
    """
    source:mqtt:
    Interprete header information
    """
    head_dict={}
    header = header.decode('utf-8')
    # some cleaning actions for false header inputs
    header = header.replace(', ',',')
    header = header.replace('deg C','deg')
    h_elem = header.strip().split()
    if not h_elem[-2].startswith('<'):
        packstr = '<'+h_elem[-2]+'B'
    else: # LEMI
        packstr = h_elem[-2]
    packstr = packstr.encode('ascii','ignore')
    lengthcode = struct.calcsize(packstr)
    si = h_elem[2]
    if not si == sensorid:
        log.msg("Different sensorids in publish address {} and header {} - please check - aborting".format(si,sensorid))
        sys.exit()
    keylist = h_elem[3].strip('[').strip(']').split(',')
    elemlist = h_elem[4].strip('[').strip(']').split(',')
    unitlist = h_elem[5].strip('[').strip(']').split(',')
    multilist = list(map(float,h_elem[6].strip('[').strip(']').split(',')))
    if debug:
        log.msg("Packing code: {}".format(packstr))
        log.msg("keylist: {}".format(keylist))
    head_dict['SensorID'] = sensorid
    sensl = sensorid.split('_')
    head_dict['SensorName'] = sensl[0]
    head_dict['SensorSerialNumber'] = sensl[1]
    head_dict['SensorRevision'] = sensl[2]
    head_dict['SensorKeys'] = ','.join(keylist)
    head_dict['SensorElements'] = ','.join(elemlist)
    head_dict['StationID'] = stationid.upper()
    # possible additional data in header (because in sensor.cfg)
    #head_dict['DataPier'] = ...
    #head_dict['SensorModule'] = ...
    #head_dict['SensorGroup'] = ...
    #head_dict['SensorDescription'] = ...
    l1 = []
    l2 = []
    for idx,key in enumerate(KEYLIST):
        if key in keylist:
            l1.append(elemlist[keylist.index(key)])
            l2.append(unitlist[keylist.index(key)])
        else:
            l1.append('')
            l2.append('')
    head_dict['ColumnContents'] = ','.join(l1[1:])
    head_dict['ColumnUnits'] = ','.join(l2[1:])
    return head_dict

def interprete_data(payload, ident, stream, sensorid):
    """
    source:mqtt:
    """
    # future: check for json payload first
    
    lines = payload.split(';') # for multiple lines send within one payload
    # allow for strings in payload !!
    array = [[] for elem in KEYLIST]
    keylist = identifier[sensorid+':keylist']
    multilist = identifier[sensorid+':multilist']
    for line in lines:
        data = line.split(',')
        timear = list(map(int,data[:7]))
        #log.msg(timear)
        time = datetime(timear[0],timear[1],timear[2],timear[3],timear[4],timear[5],timear[6])
        array[0].append(date2num(time))
        for idx, elem in enumerate(keylist):
            index = KEYLIST.index(elem)
            if not elem.endswith('time'):
                if elem in NUMKEYLIST:
                    array[index].append(float(data[idx+7])/float(multilist[idx]))
                else:
                    array[index].append(data[idx+7])

    return np.asarray([np.asarray(elem) for elem in array])


def on_connect(client, userdata, flags, rc):
    log.msg("Connected with result code {}".format(str(rc)))
    #qos = 1
    log.msg("Setting QOS (Quality of Service): {}".format(qos))
    if str(rc) == '0':
        log.msg("Everything fine - continuing")
    elif str(rc) == '5':
        log.msg("Broker eventually requires authentication - use options -u and -P")
    # important obtain subscription from some config file or provide it directly (e.g. collector -a localhost -p 1883 -t mqtt -s wic)
    if stationid == 'all':
        substring = '/#'
    else:
        substring = stationid+'/#'
    log.msg("Subscribing to: {}".format(substring))
    client.subscribe(substring,qos=qos)

def on_message(client, userdata, msg):
    global verifiedlocation
    arrayinterpreted = False
    if stationid == 'all':
        stid = msg.topic.split('/')[0]
    else:
        stid = stationid
    sensorid = msg.topic.replace(stid,"").replace('/','').replace('meta','').replace('data','').replace('dict','')
    # define a new data stream for each non-existing sensor
    if not instrument == '':
        if not sensorid.find(instrument) > -1:
            return
    metacheck = identifier.get(sensorid+':packingcode','')
    if msg.topic.endswith('meta') and metacheck == '':
        log.msg("Found basic header:{}".format(str(msg.payload)))
        log.msg("Quality od Service (QOS):{}".format(str(msg.qos)))
        analyse_meta(str(msg.payload),sensorid)
        if not sensorid in headdict:
            headdict[sensorid] = msg.payload
            # create stream.header dictionary and it here
            headstream[sensorid] = create_head_dict(str(msg.payload),sensorid)
            if debug:
                log.msg("New headdict: {}".format(headdict))
    elif msg.topic.endswith('dict') and sensorid in headdict:
        #log.msg("Found Dictionary:{}".format(str(msg.payload)))
        head_dict = headstream[sensorid]
        for elem in str(msg.payload).split(','):
            keyvaluespair = elem.split(':')
            try:
                if not keyvaluespair[1] in ['-','-\n','-\r\n']:
                    head_dict[keyvaluespair[0]] = keyvaluespair[1].strip()
            except:
                pass
        if debug:
            log.msg("Dictionary now looks like {}".format(headstream[sensorid]))
    elif msg.topic.endswith('data'):
        #if debug:
        #    log.msg("Found data:", str(msg.payload), metacheck)
        if not metacheck == '':
            if 'file' in destination:
                # Import module for writing data from acquistion
                # -------------------
                #if debug:
                #    log.msg(sensorid, metacheck, msg.payload)  # payload can be split
                # Check whether header is already identified 
                # -------------------
                if sensorid in headdict:
                    header = headdict.get(sensorid)
                    packcode = metacheck.strip('<')[:-1] # drop leading < and final B
                    # temporary code - too be deleted when lemi protocol has been updated
                    if packcode.find('4cb6B8hb30f3Bc') >= 0:
                        header = header.replace('<4cb6B8hb30f3BcBcc5hL 169\n','6hLffflll {}'.format(struct.calcsize('<6hLffflll')))
                        packcode = '6hLffflll' 
                    arrayelem = msg.payload.split(';')
                    for ar in arrayelem:
                        datearray = ar.split(',')
                        # identify string values in packcode
                        # -------------------
                        # convert packcode numbers
                        cpack = []
                        for c in packcode:
                            if c.isdigit():
                                digit = int(c)
                            else:
                                cpack.extend([c] * digit)
                                digit=1
                        cpackcode = "".join(cpack) 
                        for i in range(len(cpackcode)):
                            if cpackcode[-i] == 's':
                                datearray[-i] = datearray[-i]
                            elif cpackcode[-i] == 'f':
                                datearray[-i] = float(datearray[-i])
                            else:
                                datearray[-i] = int(float(datearray[-i]))
                        # pack data using little endian byte order
                        data_bin = struct.pack('<'+packcode,*datearray)
                        # Check whether destination path has been verified already 
                        # -------------------
                        if not verifiedlocation:
                            if not location in [None,''] and os.path.exists(location):
                                verifiedlocation = True
                            else:
                                log.msg("File: destination location {} is not accessible".format(location))
                                log.msg("      -> please use option l (e.g. -l '/my/path') to define") 
                        if verifiedlocation:
                            filename = "{}-{:02d}-{:02d}".format(datearray[0],datearray[1],datearray[2])
                            acs.dataToFile(location, sensorid, filename, data_bin, header)
            if 'websocket' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                for idx,el in enumerate(stream.ndarray[0]):
                    time = num2date(el).replace(tzinfo=None)
                    msecSince1970 = int((time - datetime(1970,1,1)).total_seconds()*1000)
                    datastring = ','.join([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    wsserver.send_message_to_all("{}: {},{}".format(sensorid,msecSince1970,datastring))
            if 'diff' in destination:
                global counter
                counter+=1
                global number
                amount = int(number)
                cover = 5
                if not arrayinterpreted:
                    ar = interprete_data(msg.payload, identifier, stream, sensorid)
                    if not sensorid in senslst:
                        senslst.append(sensorid)
                        st.append(DataStream([],{},ar))
                    idx = senslst.index(sensorid)
                    st[idx].extend(stream.container,{'SensorID':sensorid},ar)
                    arrayinterpreted = True
                st[idx].ndarray = np.asarray([np.asarray(el[-cover:]) for el in st[idx].ndarray])
                if len(st) < 2:
                     print ("Not enough streams for subtraction yet")
                try:
                    if counter > amount:
                        counter = 0
                        sub = subtractStreams(st[0],st[1])
                        try:
                            part1 = (st[0].header.get('SensorID').split('_')[1])
                        except:
                            part1 = 'unkown'
                        try:
                            part2 = (st[1].header.get('SensorID').split('_')[1])
                        except:
                            part2 = 'unkown'
                        name = "Diff_{}-{}_0001".format(part1,part2)
                        # get head line for pub
                        #name = "diff_xxx_0001"
                        keys = sub._get_key_headers(numerical=True)
                        ilst = [KEYLIST.index(key) for key in keys]
                        keystr = "[{}]".format(",".join(keys))                     
                        #takeunits =  ### take from st[0]
                        packcode = "6hL{}".format("".join(['l']*len(keys)))
                        multi = "[{}]".format(",".join(['1000']*len(keys)))
                        unit = "[{}]".format(",".join(['arb']*len(keys)))
                        head = "# MagPyBin {} {} {} {} {} {} {}".format(name, keystr, keystr, unit, multi, packcode, struct.calcsize('<'+packcode))
                        #print (head)
                        # get data line for pub
                        time = sub.ndarray[0][-1]
                        timestr = (datetime.strftime(num2date(float(time)).replace(tzinfo=None), "%Y,%m,%d,%H,%M,%S,%f"))
                        val = [sub.ndarray[i][-1] for i in ilst]
                        if len(val) > 1:
                            valstr = ",".join(int(val*1000))
                        else:
                            valstr = int(val[0]*1000)
                        data = "{},{}".format(timestr,valstr)
                        #print (data)
                        topic = "wic/{}".format(name)
                        client.publish(topic+"/data", data, qos=0)
                        client.publish(topic+"/meta", head, qos=0)
                except:
                    print ("Found error in subtraction")
            if 'stdout' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                for idx,el in enumerate(stream.ndarray[0]):
                    time = num2date(el).replace(tzinfo=None)
                    datastring = ','.join([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    log.msg("{}: {},{}".format(sensorid,time,datastring))
            elif 'db' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                # create a stream.header
                #if debug:
                #    log.msg(stream.ndarray)
                stream.header = headstream[sensorid]
                if debug:
                    log.msg("writing header: {}".format(headstream[sensorid]))
                # Could be handled by an option like revision="0001"
                # if revision: as below else writeDB(db,stream)
                writeDB(db,stream,tablename="{}_{}".format(sensorid,'0001'))
                #sys.exit()
            elif 'stringio' in destination:
                if not arrayinterpreted:
                    stream.ndarray = interprete_data(msg.payload, identifier, stream, sensorid)
                    #streamdict[sensorid] = stream.ndarray  # to store data from different sensors
                    arrayinterpreted = True
                for idx,el in enumerate(stream.ndarray[0]):
                    time = num2date(el).replace(tzinfo=None)
                    date = datetime.strftime(time,"%Y-%m-%d %H:%M:%S.%f")
                    linelist = list(map(str,[el,date]))
                    linelist.extend([str(val[idx]) for i,val in enumerate(stream.ndarray) if len(val) > 0 and not i == 0])
                    line = ','.join(linelist)
                    eol = '\r\n'
                    output.write(line+eol)
            else:
                pass
        else:
            log.msg("{}  {}".format(msg.topic, str(msg.payload)))
    if msg.topic.endswith('meta') and 'websocket' in destination:
        # send header info for each element (# sensorid   nr   key   elem   unit) 
        analyse_meta(str(msg.payload),sensorid)
        for (i,void) in enumerate(identifier[sensorid+':keylist']):
            jsonstr={}
            jsonstr['sensorid'] = sensorid
            jsonstr['nr'] = i
            jsonstr['key'] = identifier[sensorid+':keylist'][i]
            jsonstr['elem'] = identifier[sensorid+':elemlist'][i]
            jsonstr['unit'] = identifier[sensorid+':unitlist'][i]
            payload = json.dumps(jsonstr)
            wsserver.send_message_to_all('# '+payload)


def main(argv):
    broker = 'localhost'  # default
    port = 1883
    timeout=60
    altbroker = ''
    user = ''
    password = ''
    logging = 'sys.stdout'
    global destination
    destination='stdout'
    global location
    location='/tmp'
    global credentials
    credentials=''
    global offset
    offset = ''
    global dbcred
    dbcred=''
    global stationid
    stationid = 'wic'
    global instrument
    instrument = ''
    global source
    source='mqtt' # projected sources: mqtt (default), wamp, mysql, postgres, etc
    global qos
    qos=0
    global debug
    debug = False
    global output
    global headstream
    headstream = {}
    #global verifiedlocation
    #verifiedlocation = False
    global dictcheck
    dictcheck = False
    global socketport
    global number
    number=1

    usagestring = 'collector.py -b <broker> -p <port> -t <timeout> -o <topic> -i <instrument> -d <destination> -l <location> -c <credentials> -r <dbcred> -q <qos> -u <user> -P <password> -s <source> -f <offset> -m <marcos> -n <number>'
    try:
        opts, args = getopt.getopt(argv,"hb:p:t:o:i:d:l:c:r:q:u:P:s:f:m:n:U",["broker=","port=","timeout=","topic=","instrument=","destination=","location=","credentials=","dbcred=","qos=","debug=","user=","password=","source=","offset=","marcos=","number="])
    except getopt.GetoptError:
        print ('Check your options:')
        print (usagestring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------')
            print ('Usage:')
            print (usagestring)
            print ('------------------------------------------------------')
            print ('Options:')
            print ('-h                             help')
            print ('-b                             set broker address: default = localhost')
            print ('-p                             set port - default is 1883')
            print ('-t                             set timeout - default is 60')
            print ('-o                             set base topic - for MARTAS this corresponds')
            print ('                               to the station ID (e.g. wic)')
            print ('                               use "-o all" to get all stationids at a specific broker')
            print ('-i                             choose instrument(s) - only sensors containing')
            print ('                               the provided string are used: ')
            print ('                               -i GSM  will access GSM90_xxx and GSM19_xyz ')
            print ('                               Default is to use all')
            print ('-d                             set destination - std.out, db, file') 
            print ('                               default is std.out') 
            print ('-l                             set location depending on destination')
            print ('                               if d="file": provide path')
            print ('                               if d="std.out": not used')
            print ('-c                             set mqtt communication credential keyword')
            print ('-q                             set mqtt quality of service (default = 0)')            
            print ('-r                             set db credential keyword')            
            print ('-s                             source protocol of data: default is mqtt')            
            print ('                               other options:')
            print ('                               -s wamp    not yet implemented.')
            print ('-f                             offset values. Can either be "db" for')
            print ('                               applying delta values from db or a string')
            print ('                               of the following format (key:value):')
            print ('                               -f "t1:3.234,x:45674.2"')
            print ('                               other options:')
            print ('-m                             marcos configuration file ')
            print ('                               e.g. "/home/cobs/marcos.cfg"')
            print ('-n                             provide a integer number ')
            print ('                               "-d diff -i GSM": difference of two GSM will')
            print ('                                                 be calculated every n th step.')
            print ('------------------------------------------------------')
            print ('Examples:')
            print ('1. Basic')
            print ('   python collector.py -b "192.168.0.100" -o wic')
            print ('2. Writing to file in directory "/my/path/"')
            print ('   python collector.py -b "192.168.0.100" -d file -l "/my/path" -o wic')
            print ('3. Writing to file and stdout')
            print ('   python collector.py -b "192.168.0.100" -d file,stdout -l "/tmp" -o wic')
            print ('4. Writing to db')
            print ('   python collector.py -b "192.168.0.100" -d db -r mydb -o wic')
            print ('   python collector.py -d "db,file" -r testdb')
            print ('5. Using configuration file')
            print ('   python collector.py -m "/path/to/marcos.cfg"')
            print ('6. Overriding individual parameters from config file')
            print ('   python collector.py -m "/path/to/marcos.cfg" -b "192.168.0.100"')
            print ('   (make sure that config is called first)')
            print ('7. Calculating differences/gradients on the fly:')
            print ('   python collector.py -d diff -i G823A -n 10')
            print ('   (will calculate the diffs of two G823A every 10th record)')
            sys.exit()
        elif opt in ("-m", "--marcos"):
            marcosfile = arg
            print ("Getting all parameters from configration file: {}".format(marcosfile))
            conf = acs.GetConf(marcosfile)
            if not conf.get('logging','') == '':
                logging = conf.get('logging').strip()
            if not conf.get('broker','') == '':
                broker = conf.get('broker').strip()
            if not conf.get('mqttport','') in ['','-']:
                port = int(conf.get('mqttport').strip())
            if not conf.get('mqttdelay','') in ['','-']:
                timeout = int(conf.get('mqttdelay').strip())
            if not conf.get('mqttuser','') in ['','-']:
                user = conf.get('mqttuser').strip()
            if not conf.get('mqttqos','') in ['','-']:
                qos = conf.get('mqttqos').strip()
            if not conf.get('mqttcredentials','') in ['','-']:
                credentials=conf.get('mqttcredentials').strip()
            if not conf.get('station','') in ['','-']:
                stationid = conf.get('station').strip()
            if not conf.get('destination','') in ['','-']:
                destination=conf.get('destination').strip()
            if not conf.get('filepath','') in ['','-']:
                location=conf.get('filepath').strip()
            if not conf.get('databasecredentials','') in ['','-']:
                dbcred=conf.get('databasecredentials').strip()
            if not conf.get('offset','') in ['','-']:
                offset = conf.get('offset').strip()
            if not conf.get('debug','') in ['','-']:
                debug = conf.get('debug').strip()
                if debug in ['True','true']:
                    debug = True
                else:
                    debug = False
            if not conf.get('socketport','') in ['','-']:
                try:
                    socketport = int(conf.get('socketport').strip())
                except:
                    print('socketport not read properly from marcos config file')
                    socketport = 5000
            source='mqtt'
        elif opt in ("-b", "--broker"):
            broker = arg
        elif opt in ("-p", "--port"):
            try:
                port = int(arg)
            except:
                port = arg
        elif opt in ("-t", "--timeout"):
            try:
                timeout = int(arg)
            except:
                timeout = arg
        elif opt in ("-o", "--topic"):
            stationid = arg
        elif opt in ("-i", "--instrument"):
            instrument = arg
        elif opt in ("-s", "--source"):
            source = arg
        elif opt in ("-d", "--destination"):
            destination = arg
        elif opt in ("-l", "--location"):
            location = arg
        elif opt in ("-c", "--credentials"):
            credentials = arg
        elif opt in ("-r", "--dbcred"):
            dbcred = arg
        elif opt in ("-q", "--qos"):
            try:
                qos = int(arg)
            except:
                qos = 0
        elif opt in ("-u", "--user"):
            user = arg
        elif opt in ("-P", "--password"):
            password = arg
        elif opt in ("-f", "--offset"):
            offset = arg
        elif opt in ("-n", "--number"):
            number = arg
        elif opt in ("-U", "--debug"):
            debug = True


    if debug:
        print ("collector strting with the following parameters:")
        print ("Logs: {}; Broker: {}; Topic/StationID: {}; MQTTport: {}; MQTTuser: {}; MQTTcredentials: {}; Data destination: {}; Filepath: {}; DB credentials: {}; Offsets: {}".format(logging, broker, stationid, port, user, credentials, destination, location, dbcred, offset))

    try:
        ##  Start Twisted logging system
        ##  ----------------------------
        if logging == 'sys.stdout':
            log.startLogging(sys.stdout)
        else:
            try:
                print (" -- Logging to {}".format(logging))
                log.startLogging(open(logging,'a'))
                log.msg("----------------")
                log.msg("  -> Logging to {}".format(logging))
            except:
                log.startLogging(sys.stdout)
                log.msg("Could not open {}. Switching log to stdout.".format(logging))
    except:
        print("Logging requires twisted module")
        sys.exit()

    log.msg("----------------")
    log.msg(" Starting collector")
    log.msg("----------------")

    if not qos in [0,1,2]:
        qos = 0
    if 'stringio' in destination:
        output = StringIO.StringIO()
    if 'file' in destination:
        if location in [None,''] and not os.path.exists(location):
            log.msg('destination "file" requires a valid path provided as location')
            log.msg(' ... aborting ...')
            sys.exit()
    if 'websocket' in destination:
        if ws_available:
            # 0.0.0.0 makes the websocket accessable from anywhere
            global wsserver
            wsserver = WebsocketServer(socketport, host='0.0.0.0')
            wsThr = threading.Thread(target=wsThread,args=(wsserver,))
            # start websocket-server in a thread as daemon, so the entire Python program exits
            wsThr.daemon = True
            log.msg('starting websocket on port '+str(socketport))
            wsThr.start()
            # start webserver as process, also as daemon (kills process, when main program ends)
            webPr = Process(target=webProcess, args=(webpath,webport))
            webPr.daemon = True
            webPr.start()
            log.msg('starting webserver on port '+str(webport))
        else:
            print("no webserver or no websocket-server available: remove 'websocket' from destination")
            sys.exit()
    if 'db' in destination:
        if dbcred in [None,'']:
            log.msg('destination "db" requires database credentials')
            log.msg('to create them use method "addcred"')
            log.msg('to provide use option -r like -r mydb')
            sys.exit()
        else:
            try:
                global db
                if debug:
                    log.msg("Connecting database {} at host {} with user {}".format(mpcred.lc(dbcred,'db'),mpcred.lc(dbcred,'host'),mpcred.lc(dbcred,'user')))
                db = mysql.connect(host=mpcred.lc(dbcred,'host'),user=mpcred.lc(dbcred,'user'),passwd=mpcred.lc(dbcred,'passwd'),db=mpcred.lc(dbcred,'db'))
            except:
                log.msg('database could not be connected')
                log.msg(' ... aborting ...')
                sys.exit()            

    if debug:
        log.msg("Option u: debug mode switched on ...")
        log.msg("------------------------------------")
        log.msg("Destination: {} {}".format(destination, location))

    if source == 'mqtt':
        client = connectclient(broker, port, timeout, credentials, user, password)
        client.loop_forever()

    elif source == 'wamp':
        log.msg("Not yet supported! -> check autobahn import, crossbario")
    else:
        log.msg("Additional protocols can be added in future...")


if __name__ == "__main__":
   main(sys.argv[1:])


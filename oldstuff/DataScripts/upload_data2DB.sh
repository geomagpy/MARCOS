#!/bin/bash

# IMPORTANT: run with bash upload.... not with sh 

# A small shell scrip to upload long time ranges to the database.
# This scrip calls the data2DB function for timeranges defined by an increment in days
# As the full data set is loaded into the memory only a limited amount of data can be
# treated at once (depending on your PC's memory and the resolution of the data
# As a typical maximal benchmark (4 GB working memory) the following increments can be used
# Smaller increments will be faster

# 10 Hz data: INCR="1" !!!!!!!!!!!  Please note: for 10Hz data and 4GB Ram set 
#                                   TENHZ to 1 to avoid memory errors when treating the data 
# 1 sec data: INCR="10"
# 60 sec data: INCR="600"

S="2014-12-02"
E="2015-02-10"
INCR="1"
SENSOR="GSM90_14245_0002"
TENHZ="0"

NINCR="0"
START=`date -d "$S" +%Y-%m-%d`
echo $START
STEP=`date -d "$S +$INCR day" +%Y-%m-%d`
echo $STEP
END=`date -d "$E" +%Y-%m-%d`
echo $END

D1=`date +%s -d "$S"`
D2=`date +%s -d "$E"`

DIFF=$((($D2-$D1)/86400))
echo $DIFF

while [ $NINCR -le $DIFF ]; do
    if [ "$NINCR" == "0" ]
        then
            START=`date -d "$S" +%Y-%m-%d`
        else
            START=`date -d "$S +$NINCR day" +%Y-%m-%d`
    fi
    NINCR=$(($NINCR+$INCR))
    OVERLAPP=$(($NINCR+1))
    if [ $TENHZ == "1" ]
        then 
            OVERLAPP=$NINCR
    fi
    STEP=`date -d "$S +$OVERLAPP day" +%Y-%m-%d`
    python /home/cobs/MARCOS/DataScripts/data2DB.py -c cobsdb -p "/srv/archive/WIC/$SENSOR/raw/*.bin" -s $SENSOR -t WIC -a "/srv/archive" -b $START -e $STEP
done


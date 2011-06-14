#!/bin/sh
# Test the config of valodator and compatibility with external websites.
# Do NOT run this script too often.

mkdir testout

./valodator.py sample/livearchive2158.cpp testout/livearchive.xml livearchive/2158
sleep 2 #sleeping is nice

./valodator.py sample/spojTEST.cpp testout/spoj.xml spoj/TEST
sleep 2

./valodator.py sample/timus1000.cpp testout/timus.xml timus/1000
sleep 2

# TJU is down 
# ./valodator.py sample/tju1001.cpp testout/tju.xml tju/1001
# sleep 2

# UVa is down
# ./valodator.py sample/uva10055.cpp testout/uva.xml uva/10055

cat testout/livearchive.xml
cat testout/spoj.xml
cat testout/timus.xml
#cat testout/tju.xml
#cat testout/uva.xml

rm -rf testout

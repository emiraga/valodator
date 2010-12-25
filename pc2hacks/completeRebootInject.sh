#!/bin/sh
#
# Don't run this script unless you are sure about what it does
#

if [ ! -e "problem_list.txt" ]; then echo "You need to make problem_list.txt"; exit; fi

killall -9 java 2>/dev/null # boo hoo

./pc2reset 2>/dev/null
if [ $? != 0 ]; then exit; fi

echo "Starting server"
./pc2server --login site1 --password site1 &

echo "Waiting 5 seconds"
sleep 5

./injector < problem_list.txt
if [ $? != 0 ]; then exit; fi

echo "Starting judge1"
./pc2judge --login judge1 --password judge1 &

echo "Starting scoreboard1"
./pc2board --login scoreboard1 --password scoreboard1 &

echo "Waiting 10 seconds"
sleep 10

echo "Starting Admin, login as 'r', and blank password"
./pc2admin &


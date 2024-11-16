#!/bin/bash

log_file='/home/kesha/wg/logs/traffic.log'
timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$timestamp Transfer bytes" >> $log_file
wg show wg0 transfer | sed 's/\t/,/g' | sed "s/^/$timestamp /g" >> $log_file


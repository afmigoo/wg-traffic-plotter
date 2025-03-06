#!/bin/bash

root=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )
log_file="$root/traffic.log"

timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$timestamp Transfer bytes" >> $log_file
wg show wg0 transfer | sed 's/\t/,/g' | sed "s/^/$timestamp /g" >> $log_file
chown www-data:hosted $log_file

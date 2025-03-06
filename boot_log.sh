#!/bin/bash

root=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )
log_file="$root/traffic.log"
timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$timestamp System boot" >> $log_file

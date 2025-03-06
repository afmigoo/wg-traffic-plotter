#!/bin/bash

root=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )
python="$root/venv/bin/python3"
script="$root/render.py"
log_file="$root/traffic.log"
wgconf_file='/etc/wireguard/wg0.conf'
output_dir="/hosted/wgstat"

timestamp="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$timestamp Transfer bytes" >> $log_file
wg show wg0 transfer | sed 's/\t/,/g' | sed "s/^/$timestamp /g" >> $log_file

$python $script $wgconf_file $log_file $output_dir


#!/bin/bash

root=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )
python="$root/venv/bin/python3"
script="$root/render.py"
log_file="$root/traffic.log"
wgconf_file='/hosted/wgstat/src/wg0_pub.conf'
output_dir="/hosted/wgstat/html"

$python $script $wgconf_file $log_file $output_dir


## Wireguard logger and plotter

Add `dump_log.sh` to crontab (or any alternative). It will log wg traffic stats.
Add `boot_log.sh` to crontab on system boot. It will log reboots (needed bc reboots reset wg stats).


`parse.py` parses the log file and renders an html file. You can add it to crontab too and host your html to see live stats.

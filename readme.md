## Wireguard logger and plotter

Add `dump_log.sh` to crontab (or any alternative). It will log wg traffic stats.
Add `boot_log.sh` to crontab on system boot. It will log reboots (needed bc reboots reset wg stats).


`render.py` parses the log file and renders a html files in `html` folder. You can add it to crontab too and host your html to see live stats.

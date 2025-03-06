## Wireguard logger and plotter

### Usage
Args: `<wg conf file> <input log file> (<output dir>)`
`<output dir>` = "./html" by default
```bash
python3 render.py wg0.conf traffic.log mystats
```
- This will render html files to ./mystats
- traffic.log can be generated using `dump_log.sh`
- wg0.conf  
    My conf file has client aliases commented above [Peer] blocks like so: (I use [wg install script](https://github.com/angristan/wireguard-install) that manages it automatically)
    ```
    ### Client peter-laptop
    [Peer]
    PublicKey = ...
    PresharedKey = ...
    AllowedIPs = ...
    ```
    So render.py just extracts peter-laptop and uses it as client name in html instead of PublicKey. For security reasons I don't recommend feeding your actual wg0.conf to the script, I feed it a copy with deleted PresharedKey and PrivateKey lines.


### Crontab scripts
- Add `dump_log.sh` to crontab (or any alternative) as root. It will log wg traffic stats. Root needed to acces `wg` command  
- Add `render.sh` to crontab as any user
- Add `boot_log.sh` to crontab on system boot as any user. It will help script keep track of reboots since `wg show` data resets on reboots


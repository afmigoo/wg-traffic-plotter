#!venv/bin/python3
from typing import List, Dict, Union
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys
import re

from jinja2 import (Environment,
                    FileSystemLoader)
#import matplotlib.pyplot as plt

root_dir = Path(__file__).parent

plot_dir = root_dir.joinpath('plots')
diff_dir = plot_dir.joinpath('diff')
total_dir = plot_dir.joinpath('total')
templates_dir = root_dir.joinpath('templates')

plot_dir.mkdir(exist_ok=True)
diff_dir.mkdir(exist_ok=True)
total_dir.mkdir(exist_ok=True)  

def restore_total(arr: List[Dict[str, Union[str, List[int]]]], inner_idx: int, new_val: int) -> int:
    """Sometimes server reboots and resets total. In this case prev val is -1
       This func restores total from before reboot if it exists."""
    if len(arr) == 0:
        return new_val
    # if prev log is reboot
    if arr[-1]['total'][inner_idx] == -1:
        # looking for last val
        last_pos = -1
        for i in range(len(arr) - 1, -1, -1):
            if arr[i]['total'][inner_idx] != -1:
                last_pos = i
                break
        # if not found we think current total is the total
        if last_pos == -1:
            return new_val
        return arr[last_pos]['total'][inner_idx] + new_val
    # if prev total is bigger than new total 
    # all totals after reboots are smaller than true total
    if arr[-1]['total'][inner_idx] > new_val:
        return arr[-1]['total'][inner_idx] + new_val
    return new_val

def calc_diff(arr: List[Dict[str, Union[str, List[int]]]], inner_idx: int, new_val: int) -> int:
    last_total = -1
    for i in range(len(arr) - 1, -1, -1):
        if arr[i]['total'][inner_idx] != -1:
            last_total = i
            break
    if last_total == -1:
        return new_val
    return new_val - arr[last_total]['total'][inner_idx]

def parse(filename: Path, client_names: Dict[str, str]) -> Dict[str, List[Dict[str, Union[str, List[int]]]]]:
    user_data = defaultdict(list)
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            timestamp_r = r'\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}'
            match = re.search(fr'\[({timestamp_r})\] (.*)', line)
            try:
                timestamp, data = match.groups()
            except Exception:
                print(f'invalid log format:\n{line}')
                exit(1)

            if data == 'System boot':
                for d in user_data.values():
                    d.append({
                        'timestamp': timestamp,
                        'total': [-1, -1],
                        'diff': [-1, -1]
                    })
            elif data == 'Transfer bytes':
                continue
            else:
                user_key, recieved, sent = data.split(',')
                # hiding public key and using client-name as user id
                if user_key in client_names:
                    user_key = client_names[user_key]
                recieved, sent = int(recieved), int(sent)

                recieved = restore_total(user_data[user_key], 0, recieved)
                sent = restore_total(user_data[user_key], 1, sent)
                rcv_diff = calc_diff(user_data[user_key], 0, recieved)
                sent_diff = calc_diff(user_data[user_key], 1, sent)
                
                user_data[user_key].append({
                    'timestamp': timestamp,
                    'total': [recieved, sent],
                    'diff': [rcv_diff, sent_diff]
                })

    return user_data

def parse_wgconf(filename: Path) -> Dict[str, str]:
    """returns dict of <client-name>: <client-pubkey>"""
    with open(filename, 'r', encoding='utf-8') as f:
        cur_client = None
        clients = {}
        for line in f:
            if line.startswith('### Client '):
                cur_client = line.removeprefix('### Client ').strip()
                continue
            if line.startswith('PublicKey = '):
                clients[line.removeprefix('PublicKey = ').strip()] = cur_client
                cur_client = None
        return clients

def byte2mib(byte: int) -> float:
    return byte / 1048576 # 1024 * 1024

def generate_plots_plt(user_data: Dict[str, List[Dict[str, Union[str, List[int]]]]]) -> None:
    return
    def plot(title, type, x, y_rcv, y_sent, path):
        plt.figure()
        plt.title(title)
        plt.xlabel('Time')
        plt.ylabel(f'Traffic {type} (MiB)')

        plt.plot(x, y_rcv, label='Recieved by server')
        plt.plot(x, y_sent, label='Sent by server')

        plt.legend()
        plt.savefig(path)
        plt.close()

    for user_key, data in user_data.items():
        timestamps = [x['timestamp'] for x in data if x['diff'][0] != -1]
        timestamps = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in timestamps]

        rcv_diff = [byte2mib(x['diff'][0]) for x in data if x['diff'][0] != -1]
        sent_diff = [byte2mib(x['diff'][1]) for x in data if x['diff'][1] != -1]
        plot(user_key, 'by hour', 
             timestamps, rcv_diff, sent_diff,
             diff_dir.joinpath(f"{user_key.replace('/', '')}.svg"))
        
        rcv_total = [byte2mib(x['total'][0]) for x in data if x['total'][0] != -1]
        sent_total = [byte2mib(x['total'][1]) for x in data if x['total'][1] != -1]
        plot(user_key, 'total', 
             timestamps, rcv_total, sent_total,
             total_dir.joinpath(f"{user_key.replace('/', '')}.svg"))
            
def generate_plots_jinja(user_data: Dict[str, List[Dict[str, Union[str, List[int]]]]], output_file: Path) -> None:
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('index.html')
    
    user_keys = list(user_data.keys())
    user_stat = list(user_data.values())

    for i in range(len(user_stat)):
        user_stat[i] = {
            'x': [x['timestamp'] for x in user_stat[i] if x['diff'][0] != -1],
            'rcv_diff': [byte2mib(x['diff'][0]) for x in user_stat[i] if x['diff'][0] != -1],
            'sent_diff': [byte2mib(x['diff'][1]) for x in user_stat[i] if x['diff'][1] != -1],
            'rcv_total': [byte2mib(x['total'][0]) for x in user_stat[i] if x['total'][0] != -1],
            'sent_total': [byte2mib(x['total'][1]) for x in user_stat[i] if x['total'][1] != -1]
        }
        assert len(user_stat[i]['x']) == \
            len(user_stat[i]['rcv_diff']) == len(user_stat[i]['sent_diff']) == \
            len(user_stat[i]['rcv_total']) == len(user_stat[i]['sent_total'])

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template.render(
            user_keys = user_keys,
            user_stat = user_stat
        ))

def main():
    def usage():
        print("Args: <wg conf file> <input log file> <output html file>"
              #" renderer - web (render html with plots) or plt (render plot images)"
        )
    wgconf_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not wgconf_file.is_file():
        print(f'file \'{wgconf_file}\' does not exist')
        usage(); exit(1)
    input_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if not input_file.is_file():
        print(f'file \'{input_file}\' does not exist')
        usage(); exit(1)
    output_file = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    if output_file is None:
        print(f'output file required')
        usage(); exit(1)

    client_names = parse_wgconf(wgconf_file)
    user_data = parse(input_file, client_names)
    for d in user_data.values():
        assert sum(x['diff'][0] for x in d if x['diff'][0] != -1) == d[-1]['total'][0]
        assert sum(x['diff'][1] for x in d if x['diff'][1] != -1) == d[-1]['total'][1]
    
    generate_plots_jinja(user_data, output_file)

if __name__ == '__main__':
    main()

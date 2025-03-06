#!venv/bin/python3
from typing import List, Dict, Union
from collections import defaultdict
from datetime import datetime, timedelta
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
html_dir = root_dir.joinpath('html')

templates_dir = root_dir.joinpath('templates')

plot_dir.mkdir(exist_ok=True)
diff_dir.mkdir(exist_ok=True)
total_dir.mkdir(exist_ok=True)

ts_format = '%Y-%m-%d %H:%M:%S'
ts_regex = r'\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}'

def calc_diff(arr: List[Dict[str, Union[str, List[int]]]], inner_idx: int, new_val: int) -> int:
    if len(arr) == 0:
        return new_val
    return new_val - arr[-1]['total'][inner_idx]

def parse(filename: Path, client_names: Dict[str, str]) -> Dict[str, List[Dict[str, Union[str, List[int]]]]]:
    user_data = defaultdict(list)
    with open(filename, 'r', encoding='utf-8') as f:
        reboot_memo = {}
        for line in f:
            match = re.search(fr'\[({ts_regex})\] (.*)', line)
            try:
                timestamp, data = match.groups()
            except Exception:
                print(f'invalid log format:\n{line}')
                exit(1)

            if data == 'System boot':
                for v, d in user_data.items():
                    if len(d) > 0:
                        reboot_memo[v] = d[-1]['total']
            elif data == 'Transfer bytes':
                continue
            else:
                user_key, recieved, sent = data.split(',')
                # hiding public key and using client-name as user id if present
                if user_key in client_names:
                    user_key = client_names[user_key]
                else:
                    user_key = user_key[:5].replace('/', '?') + "*" * 3
                
                recieved, sent = int(recieved), int(sent)
                if user_key in reboot_memo:
                    recieved += reboot_memo[user_key][0]
                    sent += reboot_memo[user_key][1]

                rcv_diff = calc_diff(user_data[user_key], 0, recieved)
                sent_diff = calc_diff(user_data[user_key], 1, sent)
                
                user_data[user_key].append({
                    'timestamp': datetime.strptime(timestamp, ts_format),
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

def byte2human(byte: int, precision: int = 1) -> str:
    """
    Convert bytes to human-readable format (from B to TiB)
    Args:
        size (int): Size in bytes
    Returns:
        str: Human-readable format string
    """
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    if byte == 0: 
        return f'0 {units[0]}'
    byte = float(abs(byte))
    index = 0
    while byte > 1024 and index < len(units) - 1:
        byte /= 1024
        index += 1
    if index == 0:
        byte = int(byte)
    else:
        byte = round(byte, precision)
    
    return f'{byte} {units[index]}'

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

def sum_x_days(u_data: list, idx: int, days: int) -> int:
    if len(u_data) == 0 or days == 0:
        return 0
    
    if days == -1: # then summ everything
        delta = None
    else:
        delta = timedelta(days=days)
    latest_ts = datetime.now()
    byte_sum = 0
    for i in range(len(u_data) - 1, -1, -1):
        if delta is None or u_data[i]['timestamp'] > latest_ts - delta:
            byte_sum += u_data[i]['diff'][idx] # idx = 0 means recieved; idx = 1 means sent
        else:
            break
    return byte_sum

def generate_plots_jinja(user_data: Dict[str, List[Dict[str, Union[datetime, List[int]]]]], output_dir: Path) -> None:
    env = Environment(loader=FileSystemLoader(templates_dir))
    plot_template = env.get_template('plot.html')
    index_template = env.get_template('index.html')
    user_dir = output_dir.joinpath('user')
    user_dir.mkdir(exist_ok=True)

    u_sum = {}
    for k, u_data in user_data.items():
        user_stat = {
            'x': [x['timestamp'].strftime(ts_format)
                  for x in u_data if x['diff'][0] != -1],
            'diff': {
                'rcv': [byte2mib(x['diff'][0]) for x in u_data if x['diff'][0] != -1],
                'sent': [byte2mib(x['diff'][1]) for x in u_data if x['diff'][1] != -1],
            },
            #'total': {
            #    'rcv': [byte2mib(x['total'][0]) for x in u_data if x['total'][0] != -1],
            #    'sent': [byte2mib(x['total'][1]) for x in u_data if x['total'][1] != -1],
            #},
        }
        u_sum[k] = {
            'rcv': {
                '1d': byte2human(sum_x_days(u_data, 0, days=1)),
                '1w': byte2human(sum_x_days(u_data, 0, days=7)),
                '1m': byte2human(sum_x_days(u_data, 0, days=30)),
                '1y': byte2human(sum_x_days(u_data, 0, days=365)),
                'all': byte2human(sum_x_days(u_data, 0, days=-1)),
            },
            'sent': {
                '1d': byte2human(sum_x_days(u_data, 1, days=1)),
                '1w': byte2human(sum_x_days(u_data, 1, days=7)),
                '1m': byte2human(sum_x_days(u_data, 1, days=30)),
                '1y': byte2human(sum_x_days(u_data, 1, days=365)),
                'all': byte2human(sum_x_days(u_data, 1, days=-1)),
            }
        }
        assert len(user_stat['x']) == \
            len(user_stat['diff']['rcv']) == len(user_stat['diff']['sent'])

        user_file = user_dir.joinpath(f'{k}.html')
        with open(user_file, 'w', encoding='utf-8') as f:
            f.write(plot_template.render(
                user_key = k,
                user_stat = user_stat,
            ))
    
    with open(output_dir.joinpath('index.html'), 'w', encoding='utf-8') as f:
        f.write(index_template.render(
            user_summary = u_sum
        ))

def main():
    def usage():
        print("Args: <wg conf file> <input log file> (<output dir>)")
    wgconf_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    input_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else html_dir

    if any((wgconf_file is None, input_file is None)):
        print(f'invalid argument set')
        usage(); exit(1)

    if not wgconf_file.is_file():
        print(f'file \'{wgconf_file}\' does not exist')
        usage(); exit(1)
    if not input_file.is_file():
        print(f'file \'{input_file}\' does not exist')
        usage(); exit(1)
    if not output_dir.is_dir():
        output_dir.mkdir()

    client_names = parse_wgconf(wgconf_file)
    user_data = parse(input_file, client_names)
    for d in user_data.values():
        assert sum(x['diff'][0] for x in d if x['diff'][0] != -1) == d[-1]['total'][0]
        assert sum(x['diff'][1] for x in d if x['diff'][1] != -1) == d[-1]['total'][1]
    
    generate_plots_jinja(user_data, output_dir)

if __name__ == '__main__':
    main()

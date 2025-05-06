import requests
from collections import defaultdict
import fnmatch

URL = 'https://pastebin.com/raw/5zvfV9Lp'
remove_domains = ['*instagram*', '*protonmail*', '*ggpht*', '*facebook*']
adblock_ips = {'127.0.0.1', '0.0.0.0'}
no_simplify_domains = ['*microsoft*', '*bing*', '*goog*', '*xbox*', '*github*']
example_file = 'example-cloaking-rules.txt'
output_file = 'cloaking-rules.txt'

response = requests.get(URL)
response.raise_for_status()
lines = response.text.splitlines()

entries = []
for line in lines:
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    parts = line.split()
    if len(parts) < 2:
        continue
    ip, host = parts[0], parts[1]
    if ip in adblock_ips:
        continue
    if any(fnmatch.fnmatch(host, pattern) for pattern in remove_domains):
        continue
    entries.append((host, ip))

groups = defaultdict(list)
for host, ip in entries:
    parts = host.split('.')
    root = '.'.join(parts[-2:]) if len(parts) >= 2 else host
    groups[root].append((host, ip))

final = []
for root, lst in groups.items():
    n = len(lst)
    count_by_ip = defaultdict(int)
    for host, ip in lst:
        count_by_ip[ip] += 1
    ip_most, cnt_most = max(count_by_ip.items(), key=lambda x: x[1])
    if cnt_most / n >= 0.8 and not any(fnmatch.fnmatch(root, pattern) for pattern in no_simplify_domains):
        final.append((root, ip_most))
    else:
        final.extend(lst)

with open(example_file, 'r', encoding='utf-8') as f:
    base = f.read()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(base.rstrip() + '\n')
    f.write('# t.me/immalware hosts\n')
    for host, ip in final:
        f.write(f"{host} {ip}\n")

print(f"Saved to {output_file}")

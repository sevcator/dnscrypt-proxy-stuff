import requests
from collections import defaultdict
import fnmatch

URL = 'https://pastebin.com/raw/5zvfV9Lp'
remove_domains = ['*instagram*', '*proton*', '*ggpht*', '*facebook*']
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

host_to_ip = defaultdict(set)
for host, ip in entries:
    host_to_ip[host].add(ip)

simplified = {}
for host in list(host_to_ip):
    parts = host.split('.')
    if len(parts) >= 3:
        root = '.'.join(parts[-2:])
        if not any(fnmatch.fnmatch(host, pattern) for pattern in no_simplify_domains):
            if root not in host_to_ip:
                simplified[root] = host_to_ip.pop(host)
            else:
                host_to_ip[root].update(host_to_ip.pop(host))

host_to_ip.update(simplified)

with open(example_file, 'r', encoding='utf-8') as f:
    base = f.read()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(base.rstrip() + '\n')
    f.write('# t.me/immalware hosts\n')
    for host in sorted(host_to_ip):
        for ip in host_to_ip[host]:
            f.write(f"{host} {ip}\n")

print(f"Saved to {output_file}")

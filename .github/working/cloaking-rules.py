import requests
from collections import defaultdict, Counter
import fnmatch

URL = 'https://pastebin.com/raw/5zvfV9Lp'
remove_domains = ['*xbox*', '*instagram*', '*proton*', '*facebook*', '*torrent*', '*ttvnw*', '*twitch*', '*deezer*', '*dzcdn*', '*weather*', '*fitbit*']
adblock_ips = {'127.0.0.1', '0.0.0.0'}
no_simplify_domains = ['*microsoft*', '*bing*', '*goog*', '*github*', '*parsec*', '*imgur*', '*oai*', '*tiktok*', '*archive.org*']
example_file = 'example-cloaking-rules.txt'
output_file = 'cloaking-rules.txt'

best_domain = 'chatgpt.com'
base_ip = None
custom_domains = ['soundcloud.com']

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
    if any(pattern.strip('*') in host for pattern in remove_domains):
        continue
    if host == best_domain and base_ip is None:
        base_ip = ip
    entries.append((host, ip))

host_to_ip = defaultdict(set)
subdomains_by_root = defaultdict(list)

for host, ip in entries:
    host_to_ip[host].add(ip)
    parts = host.split('.')
    if len(parts) >= 2:
        root = '.'.join(parts[-2:])
        subdomains_by_root[root].append((host, ip))

final_hosts = {}

for root, items in subdomains_by_root.items():
    domain_ips = Counter()
    all_hosts = set(host for host, _ in items)
    no_simplify = any(fnmatch.fnmatch(host, pattern) for host in all_hosts for pattern in no_simplify_domains)

    if no_simplify:
        for host, ip in items:
            final_hosts.setdefault(host, set()).add(ip)
    else:
        for host, ip in items:
            if host == root:
                domain_ips[ip] += 5
            else:
                domain_ips[ip] += 1

        most_common_ip, count = domain_ips.most_common(1)[0]

        root_in_items = any(h == root for h, _ in items)
        if root_in_items or any(h.endswith('.' + root) for h, _ in items):
            final_hosts[root] = {most_common_ip}

        for host, ip in items:
            if host != root and ip != most_common_ip:
                final_hosts.setdefault(host, set()).add(ip)

if base_ip:
    for custom_domain in custom_domains:
        final_hosts.setdefault(custom_domain, set()).add(base_ip)

with open(example_file, 'r', encoding='utf-8') as f:
    base = f.read()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(base.rstrip() + '\n\n')
    f.write('# t.me/immalware hosts\n')
    for host in sorted(final_hosts):
        if host not in custom_domains:
            for ip in sorted(final_hosts[host]):
                f.write(f"{host} {ip}\n")
    f.write('\n# custom t.me/immalware hosts\n')
    for host in sorted(custom_domains):
        if host in final_hosts:
            for ip in sorted(final_hosts[host]):
                f.write(f"{host} {ip}\n")

print(f"Saved to {output_file}")

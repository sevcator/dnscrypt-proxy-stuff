import base64
import fnmatch
import secrets
import ssl
import struct
import urllib.request
from collections import defaultdict, Counter

import requests

URL = 'https://raw.githubusercontent.com/ImMALWARE/dns.malw.link/refs/heads/master/hosts'
remove_domains = ['*xbox*', '*instagram*', '*proton*', '*facebook*', '*torrent*', '*twitch*', '*deezer*', '*dzcdn*', '*weather*', '*fitbit*', '*ggpht*', '*github*', '*tiktok*', '*imgur*', '*4pda*', '*malw.link*']
adblock_ips = {'127.0.0.1', '0.0.0.0'}
no_simplify_domains = ['*microsoft*', '*bing*', '*goog*', '*github*', '*parsec*', '*oai*', '*archive.org*', '*ttvnw*', '*spotify*', '*scdn.co*', '*clashroyale*', '*clashofclans*', '*brawlstars*', '*supercell*']
example_file = 'example-cloaking-rules.txt'
output_file = 'cloaking-rules-2.txt'

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
COMSS_DOH_ENDPOINTS = ['https://dns.comss.one/dns-query', 'https://router.comss.one/dns-query']
TARGET_KEYWORDS = ['*anthropic*', '*claude*', '*openai*', '*chatgpt*', '*google*', '*grok*', '*microsoft*', '*bing*']
COMSS_CACHE = {}


def encode_qname(name):
    parts = name.strip('.').split('.')
    encoded = bytearray()
    for part in parts:
        label = part.encode('idna')
        encoded.append(len(label))
        encoded.extend(label)
    encoded.append(0)
    return bytes(encoded)


def build_dns_query(name):
    transaction_id = secrets.token_bytes(2)
    flags = struct.pack('>H', 0x0100)
    qdcount = struct.pack('>H', 1)
    ancount = struct.pack('>H', 0)
    nscount = struct.pack('>H', 0)
    arcount = struct.pack('>H', 0)
    question = encode_qname(name) + struct.pack('>HH', 1, 1)
    return b''.join([transaction_id, flags, qdcount, ancount, nscount, arcount, question])


def read_name(data, offset):
    labels = []
    jumped = False
    original_offset = offset
    seen_offsets = set()
    while True:
        if offset >= len(data):
            return '', len(data)
        if offset in seen_offsets:
            return '.'.join(labels), (original_offset if jumped else offset)
        seen_offsets.add(offset)
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                return '', len(data)
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                original_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        label = data[offset:offset + length]
        labels.append(label.decode('utf-8', 'ignore'))
        offset += length
    return '.'.join(labels), (original_offset if jumped else offset)


def parse_dns_message(data):
    if len(data) < 12:
        return set()
    header = struct.unpack('>6H', data[:12])
    qdcount = header[2]
    ancount = header[3]
    offset = 12
    for _ in range(qdcount):
        _, offset = read_name(data, offset)
        offset += 4
    ips = set()
    for _ in range(ancount):
        _, offset = read_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, rclass, ttl, rdlen = struct.unpack_from('>HHIH', data, offset)
        offset += 10
        rdata = data[offset:offset + rdlen]
        offset += rdlen
        if rtype == 1 and rclass == 1 and rdlen == 4:
            ips.add('.'.join(str(b) for b in rdata))
    return ips


def doh_wire(base, name):
    query = build_dns_query(name)
    payload = base64.urlsafe_b64encode(query).decode().rstrip('=')
    url = f"{base}?dns={payload}"
    request = urllib.request.Request(
        url,
        headers={
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept': 'application/dns-message',
        },
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, context=context, timeout=10) as response:
        if response.status != 200:
            return set()
        data = response.read()
    return parse_dns_message(data)


def resolve_via_comss(name):
    key = name.lower().rstrip('.')
    if key in COMSS_CACHE:
        return COMSS_CACHE[key]

    ips = set()
    for base in COMSS_DOH_ENDPOINTS:
        try:
            ips |= doh_wire(base, name)
        except Exception as exc:
            print(f"Failed to resolve {name} via {base}: {exc}")
    COMSS_CACHE[key] = ips
    return ips


def needs_comss_override(host):
    host_l = host.lower()
    return any(fnmatch.fnmatch(host_l, pattern.lower()) for pattern in TARGET_KEYWORDS)

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

for host in list(final_hosts):
    if needs_comss_override(host):
        comss_ips = resolve_via_comss(host)
        if comss_ips:
            final_hosts[host] = comss_ips

with open(example_file, 'r', encoding='utf-8') as f:
    base = f.read()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(base.rstrip() + '\n\n')
    f.write('# t.me/immalware hosts + comss dns\n')
    for host in sorted(final_hosts):
        is_no_simplify = any(fnmatch.fnmatch(host, pattern) for pattern in no_simplify_domains)
        prefix = '=' if is_no_simplify else ''
        for ip in sorted(final_hosts[host]):
            f.write(f"{prefix}{host} {ip}\n")

print(f"Saved to {output_file}")


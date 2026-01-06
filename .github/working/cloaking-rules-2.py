from __future__ import annotations

import base64
import fnmatch
import secrets
import ssl
import struct
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests

REMOVE_PATTERNS = [
    "*xbox*",
    "*instagram*",
    "*proton*",
    "*facebook*",
    "*torrent*",
    "*twitch*",
    "*deezer*",
    "*dzcdn*",
    "*weather*",
    "*fitbit*",
    "*ggpht*",
    "*github*",
    "*tiktok*",
    "*imgur*",
    "*4pda*",
    "*malw.link*",
]
ADBLOCK_IPS = {"127.0.0.1", "0.0.0.0"}
NO_SIMPLIFY_PATTERNS = [
    "*microsoft*",
    "*bing*",
    "*goog*",
    "*github*",
    "*parsec*",
    "*oai*",
    "*archive.org*",
    "*ttvnw*",
    "*spotify*",
    "*scdn.co*",
    "*clashroyale*",
    "*clashofclans*",
    "*brawlstars*",
    "*supercell*",
]
SOURCE_MAP: Dict[str, str] = {
    "https://raw.githubusercontent.com/ImMALWARE/dns.malw.link/refs/heads/master/hosts": "immalware hosts",
    "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/hosts": "Flowseal hosts",
}
EXAMPLE_FILE = Path("example-cloaking-rules.txt")
OUTPUT_FILE = Path("cloaking-rules-2.txt")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
COMSS_DOH_ENDPOINTS = ["https://dns.comss.one/dns-query", "https://router.comss.one/dns-query"]
TARGET_KEYWORDS = [
    "*anthropic*",
    "*claude*",
    "*openai*",
    "*chatgpt*",
    "*google*",
    "*grok*",
    "*microsoft*",
    "*bing*",
]
COMSS_CACHE: Dict[str, set[str]] = {}


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def iter_entries(hosts_text: str) -> Iterable[Tuple[str, str]]:
    for raw_line in hosts_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ip, host = parts[0], parts[1]
        if ip in ADBLOCK_IPS:
            continue
        if any(fnmatch.fnmatch(host, pattern) for pattern in REMOVE_PATTERNS):
            continue
        yield host, ip


def simplify_hosts(entries: Iterable[Tuple[str, str]]) -> Dict[str, set[str]]:
    subdomains: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for host, ip in entries:
        parts = host.split(".")
        if len(parts) < 2:
            continue
        root = ".".join(parts[-2:])
        subdomains[root].append((host, ip))

    final_hosts: Dict[str, set[str]] = {}
    for root, items in subdomains.items():
        all_hosts = {host for host, _ in items}
        no_simplify = any(
            fnmatch.fnmatch(host, pattern)
            for host in all_hosts
            for pattern in NO_SIMPLIFY_PATTERNS
        )
        if no_simplify:
            for host, ip in items:
                final_hosts.setdefault(host, set()).add(ip)
            continue

        domain_ips = Counter()
        for host, ip in items:
            domain_ips[ip] += 5 if host == root else 1

        most_common_ip, _ = domain_ips.most_common(1)[0]
        final_hosts.setdefault(root, set()).add(most_common_ip)
        for host, ip in items:
            if host != root and ip != most_common_ip:
                final_hosts.setdefault(host, set()).add(ip)
    return final_hosts


def encode_qname(name: str) -> bytes:
    parts = name.strip(".").split(".")
    encoded = bytearray()
    for part in parts:
        label = part.encode("idna")
        encoded.append(len(label))
        encoded.extend(label)
    encoded.append(0)
    return bytes(encoded)


def build_dns_query(name: str) -> bytes:
    transaction_id = secrets.token_bytes(2)
    flags = struct.pack(">H", 0x0100)
    header = b"".join(
        [
            transaction_id,
            flags,
            struct.pack(">H", 1),
            struct.pack(">H", 0),
            struct.pack(">H", 0),
            struct.pack(">H", 0),
        ]
    )
    question = encode_qname(name) + struct.pack(">HH", 1, 1)
    return header + question


def read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: List[str] = []
    jumped = False
    original_offset = offset
    seen_offsets = set()
    while True:
        if offset >= len(data):
            return "", len(data)
        if offset in seen_offsets:
            return ".".join(labels), original_offset if jumped else offset
        seen_offsets.add(offset)
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                return "", len(data)
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                original_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        label = data[offset : offset + length]
        labels.append(label.decode("utf-8", "ignore"))
        offset += length
    return ".".join(labels), original_offset if jumped else offset


def parse_dns_message(data: bytes) -> set[str]:
    if len(data) < 12:
        return set()
    header = struct.unpack(">6H", data[:12])
    qdcount, ancount = header[2], header[3]
    offset = 12
    for _ in range(qdcount):
        _, offset = read_name(data, offset)
        offset += 4
    ips: set[str] = set()
    for _ in range(ancount):
        _, offset = read_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, rclass, _, rdlen = struct.unpack_from(">HHIH", data, offset)
        offset += 10
        rdata = data[offset : offset + rdlen]
        offset += rdlen
        if rtype == 1 and rclass == 1 and rdlen == 4:
            ips.add(".".join(str(b) for b in rdata))
    return ips


def doh_wire(base: str, name: str) -> set[str]:
    query = build_dns_query(name)
    payload = base64.urlsafe_b64encode(query).decode().rstrip("=")
    url = f"{base}?dns={payload}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/dns-message"},
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, context=context, timeout=10) as response:
        if response.status != 200:
            return set()
        data = response.read()
    return parse_dns_message(data)


def resolve_via_comss(name: str) -> set[str]:
    key = name.lower().rstrip(".")
    if key in COMSS_CACHE:
        return COMSS_CACHE[key]

    ips: set[str] = set()
    for base in COMSS_DOH_ENDPOINTS:
        try:
            ips |= doh_wire(base, name)
        except Exception as exc:  # pragma: no cover - network dependent
            print(f"Failed to resolve {name} via {base}: {exc}")
    COMSS_CACHE[key] = ips
    return ips


def needs_comss_override(host: str) -> bool:
    host_l = host.lower()
    return any(fnmatch.fnmatch(host_l, pattern.lower()) for pattern in TARGET_KEYWORDS)


def apply_comss_overrides(hosts: Dict[str, set[str]]) -> Dict[str, set[str]]:
    updated = dict(hosts)
    for host in list(updated):
        if needs_comss_override(host):
            comss_ips = resolve_via_comss(host)
            if comss_ips:
                updated[host] = comss_ips
    return updated


def write_sections(
    example_block: str, sections: Iterable[tuple[str, Dict[str, set[str]]]]
) -> None:
    lines: List[str] = [example_block.strip(), ""]
    for title, hosts in sections:
        lines.append(f"# {title}")
        for host in sorted(hosts):
            prefix = "=" if any(fnmatch.fnmatch(host, p) for p in NO_SIMPLIFY_PATTERNS) else ""
            for ip in sorted(hosts[host]):
                lines.append(f"{prefix}{host} {ip}")
        lines.append("")
    OUTPUT_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_section(url: str, title: str) -> tuple[str, Dict[str, set[str]]]:
    hosts_text = fetch_text(url)
    simplified = simplify_hosts(iter_entries(hosts_text))
    with_overrides = apply_comss_overrides(simplified)
    return title, with_overrides


def main() -> int:
    example_block = EXAMPLE_FILE.read_text(encoding="utf-8")
    sections = [build_section(url, title) for url, title in SOURCE_MAP.items()]
    write_sections(example_block, sections)
    print(f"Saved {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

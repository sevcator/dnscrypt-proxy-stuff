from __future__ import annotations

import fnmatch
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
OUTPUT_FILE = Path("cloaking-rules.txt")


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
    return title, simplified


def main() -> int:
    example_block = EXAMPLE_FILE.read_text(encoding="utf-8")
    sections = [build_section(url, title) for url, title in SOURCE_MAP.items()]
    write_sections(example_block, sections)
    print(f"Saved {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


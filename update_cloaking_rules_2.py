import collections
import ipaddress
import json
from pathlib import Path
from urllib import error, parse, request

HOSTS_URL = "https://raw.githubusercontent.com/ImMALWARE/dns.malw.link/refs/heads/master/hosts"
EXAMPLE_HEADER_PATH = Path(__file__).with_name("example-cloaking-rules.txt")
DOH_ENDPOINTS = {
    "comss": "https://dns.comss.one/dns-query",
    "google": "https://dns.google/dns-query",
    "cloudflare": "https://dns.cloudflare.com/dns-query",
}
HEADERS = {
    "Accept": "application/dns-json",
    "User-Agent": "dnscrypt-proxy-cloaking-updater/1.0",
}
TIMEOUT = 10


def http_get(url: str, params: dict[str, str] | None = None) -> str:
    if params:
        url = f"{url}?{parse.urlencode(params)}"
    req = request.Request(url, headers=HEADERS)
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        raise SystemExit(f"Failed to fetch {url}: {exc}") from exc


def fetch_hosts(url: str) -> list[tuple[str, str]]:
    text = http_get(url)
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ip, host = parts[0], parts[1]
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        entries.append((host.lower(), ip))
    return entries


def query_doh(endpoint: str, name: str) -> list[str]:
    try:
        text = http_get(endpoint, {"name": name, "type": "A"})
    except SystemExit:
        return []
    except Exception:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    answers = data.get("Answer") or []
    ips: set[str] = set()
    for answer in answers:
        if str(answer.get("type")) != "1":
            continue
        ip = answer.get("data")
        try:
            if ip:
                ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError:
            continue
        ips.add(ip)
    return sorted(ips)


def get_base_domain(host: str) -> str:
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    return ".".join(labels[-2:])


def load_header() -> list[str]:
    if not EXAMPLE_HEADER_PATH.exists():
        raise SystemExit(
            "example-cloaking-rules.txt was not found alongside the script."
        )
    header: list[str] = []
    with EXAMPLE_HEADER_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                break
            header.append(line.rstrip("\n"))
    while header and not header[-1]:
        header.pop()
    return header


def main() -> None:
    entries = fetch_hosts(HOSTS_URL)
    hosts = sorted({host for host, _ in entries})

    cache: dict[str, dict[str, list[str]]] = {}
    for host in hosts:
        cache[host] = {}
        for provider, endpoint in DOH_ENDPOINTS.items():
            cache[host][provider] = query_doh(endpoint, host)

    filtered: dict[str, dict[tuple[str, ...], list[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )

    for host in hosts:
        comss_ips = cache[host]["comss"]
        google_ips = cache[host]["google"]
        cloudflare_ips = cache[host]["cloudflare"]
        if not comss_ips:
            continue
        if comss_ips == google_ips and comss_ips == cloudflare_ips:
            continue
        if comss_ips == google_ips or comss_ips == cloudflare_ips:
            continue
        base = get_base_domain(host)
        filtered[base][tuple(comss_ips)].append(host)

    output_lines = load_header()
    output_lines.extend(
        [
            "",
            "# Generated automatically from dns.malw.link hosts",
            "# Only includes hosts where dns.comss.one disagrees with dns.google and dns.cloudflare",
            "",
            "# comss dns results",
        ]
    )

    final_entries: list[tuple[str, str]] = []

    for base in sorted(filtered):
        ip_groups = filtered[base]
        if len(ip_groups) == 1:
            (ips_tuple, hosts_list), = ip_groups.items()
            name_to_use = base
            for ip in ips_tuple:
                final_entries.append((name_to_use, ip))
        else:
            for ips_tuple, hosts_list in ip_groups.items():
                for host in sorted(hosts_list):
                    name_to_use = f"={host}"
                    for ip in ips_tuple:
                        final_entries.append((name_to_use, ip))

    for name, ip in sorted(final_entries):
        output_lines.append(f"{name} {ip}")

    path = Path(__file__).with_name("cloaking-rules-2.txt")
    path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

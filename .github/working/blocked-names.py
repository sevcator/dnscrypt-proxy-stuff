from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import requests

EXAMPLE_FILE = Path("example-blocked-names.txt")
CUSTOM_FILE = Path("custom-hosts.txt")
OUTPUT_FILE = Path("blocked-names.txt")

SOURCE_MAP: Dict[str, str] = {
    "https://badmojr.github.io/1Hosts/Lite/hosts.txt": "schakal hosts",
}


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_domains(hosts_text: str) -> List[str]:
    domains: List[str] = []
    for raw_line in hosts_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "localhost" in line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ip, host = parts[0], parts[1]
        if ip.startswith("127.") or ip.startswith("0.0.0.0") or ip.startswith("::1"):
            continue
        domains.append(host)
    return domains


def write_sections(
    example_block: str, sections: Iterable[tuple[str, Iterable[str]]]
) -> None:
    lines: List[str] = [example_block.strip(), ""]
    for title, body in sections:
        lines.append(f"# {title}")
        for item in body:
            lines.append(item)
        lines.append("")
    OUTPUT_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    example_blocked = EXAMPLE_FILE.read_text(encoding="utf-8").strip()
    sections = []
    for url, title in SOURCE_MAP.items():
        domains = extract_domains(fetch_text(url))
        sections.append((title, domains))

    custom_blocked = CUSTOM_FILE.read_text(encoding="utf-8").strip()
    sections.append(("custom blocklist", custom_blocked.splitlines()))

    write_sections(example_blocked, sections)
    print(f"Saved {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

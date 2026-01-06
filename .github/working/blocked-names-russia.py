#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Set

import requests

EXAMPLE_PATH = Path("example-blocked-names.txt")
OUTPUT_PATH = Path("blocked-names-russia.txt")

SOURCE_MAP: Dict[str, str] = {
    "https://schakal.ru/hosts/alive_hosts_ru_com.txt": "schakal.ru alive hosts",
}

_IP_ADDRESS_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def should_include_domain(domain: str) -> bool:
    return (
        domain.endswith(".ru")
        or domain.endswith(".su")
        or ".vk." in domain
        or "yandex." in domain
        or "russia" in domain
    )


def extract_domains(hosts_text: str) -> List[str]:
    matches: List[str] = []
    seen: Set[str] = set()
    for raw_line in hosts_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        if _IP_ADDRESS_RE.match(tokens[0]):
            tokens = tokens[1:]
        for token in tokens:
            domain = token.strip().lower()
            if not domain or domain in seen:
                continue
            if domain == "yandex.ru":
                continue
            if should_include_domain(domain):
                seen.add(domain)
                matches.append(domain)
    return matches


def write_output(example_text: str, sections: Iterable[tuple[str, Iterable[str]]]) -> None:
    lines: List[str] = [example_text.strip(), "", "# main yandex domain", "=yandex.ru", ""]
    for title, domains in sections:
        lines.append(f"# {title}")
        lines.extend(domains)
        lines.append("")
    OUTPUT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    example_text = EXAMPLE_PATH.read_text(encoding="utf-8-sig")
    sections = []
    for url, title in SOURCE_MAP.items():
        domains = extract_domains(fetch_text(url))
        sections.append((title, domains))
    write_output(example_text, sections)
    print(f"Saved {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

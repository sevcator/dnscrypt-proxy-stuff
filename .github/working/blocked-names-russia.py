#!/usr/bin/env python3
"""Generate a Russia-focused blocked names list for dnscrypt-proxy."""

from __future__ import annotations

import pathlib
import re
import sys
import urllib.error
import urllib.request
from typing import Iterable, List, Set

REPO_ROOT = pathlib.Path(__file__).resolve().parent
EXAMPLE_PATH = REPO_ROOT / "example-blocked-names.txt"
HOSTS_URL = "https://o0.pages.dev/Pro/hosts.txt"
OUTPUT_PATH = REPO_ROOT / "blocked-names-russia.txt"

_IP_ADDRESS_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def read_text_from_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(request) as response:  # type: ignore[call-arg]
        encoding = response.headers.get_content_charset("utf-8")
        return response.read().decode(encoding)


def load_example_text() -> str:
    try:
        return EXAMPLE_PATH.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Missing {EXAMPLE_PATH.name}. Place the file in the repository root."
        ) from exc


def load_hosts_text() -> str:
    try:
        return read_text_from_url(HOSTS_URL)
    except urllib.error.URLError as exc:  # pragma: no cover - depends on network
        raise RuntimeError(f"Unable to download {HOSTS_URL}: {exc}") from exc


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

            if should_include_domain(domain):
                if domain == "yandex.ru":
                    continue
                seen.add(domain)
                matches.append(domain)

    return matches


def should_include_domain(domain: str) -> bool:
    if domain.endswith(".ru"):
        return True
    if domain.endswith(".su"):
        return True
    if ".vk." in domain:
        return True
    if "yandex." in domain:
        return True
    if "russia" in domain:
        return True
    return False


def extract_header_lines(example_text: str) -> List[str]:
    """Return the header block from dnscrypt-proxy's example list."""

    header_lines: List[str] = []
    in_header = False

    for line in example_text.splitlines():
        stripped = line.lstrip()

        if stripped.startswith("#"):
            header_lines.append(line)
            in_header = True
            continue

        if in_header and not stripped:
            header_lines.append(line)
            continue

        if in_header:
            break

    if not header_lines:
        raise RuntimeError("Unexpected example header format")

    return header_lines


def compose_output(example_text: str, domains: Iterable[str]) -> str:
    lines: List[str] = []
    lines.extend(extract_header_lines(example_text))
    lines.append("")
    lines.append("# main yandex domain")
    lines.append("=yandex.ru")
    lines.append("")
    lines.append(f"# from {HOSTS_URL}")
    lines.extend(domains)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    example_text = load_example_text()
    hosts_text = load_hosts_text()
    domains = extract_domains(hosts_text)
    output_text = compose_output(example_text, domains)
    OUTPUT_PATH.write_text(output_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

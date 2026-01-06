#!/usr/bin/env python3
from __future__ import annotations

import ipaddress
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


CURL_TIMEOUT = 10


class AlternativeAddressError(Exception):
    pass


def ensure_curl_available() -> None:
    if not shutil.which("curl"):
        raise AlternativeAddressError("curl executable is required but was not found in PATH")


def load_targets(path: Path) -> List[str]:
    if not path.exists():
        raise AlternativeAddressError(f"Target file not found: {path}")
    targets: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        targets.append(line)
    if not targets:
        raise AlternativeAddressError("target-addresses.txt does not contain any domains")
    return targets


def resolve_ips(domain: str) -> List[str]:
    infos = socket.getaddrinfo(domain, None)
    ips: List[str] = []
    seen = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip = sockaddr[0]
        if ip in seen:
            continue
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue
        compact = ip_obj.compressed
        ips.append(compact)
        seen.add(compact)
    return ips


def run_curl(args: Sequence[str]) -> bool:
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def probe_domain_ip(domain: str, ip: str) -> bool:
    resolve_arg_ip = ip
    direct_ip = ip
    if ":" in ip:
        resolve_arg_ip = f"[{ip}]"
        direct_ip = f"[{ip}]"
    https_cmd = [
        "curl",
        "--max-time",
        str(CURL_TIMEOUT),
        "--resolve",
        f"{domain}:443:{resolve_arg_ip}",
        f"https://{domain}/",
        "-s",
        "-S",
        "-o",
        os.devnull,
    ]
    if run_curl(https_cmd):
        return True
    http_cmd = [
        "curl",
        "--max-time",
        str(CURL_TIMEOUT),
        f"http://{direct_ip}/",
        "-s",
        "-S",
        "-o",
        os.devnull,
    ]
    return run_curl(http_cmd)


def pick_working_ip(domain: str, ips: Iterable[str]) -> Optional[str]:
    for ip in ips:
        if probe_domain_ip(domain, ip):
            return ip
    return None


def write_lines(path: Path, lines: Iterable[str]) -> None:
    text_lines = list(lines)
    text = "\n".join(text_lines)
    if text_lines:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def combine_with_rules(resolved_hosts: Path, rules_path: Path, output_path: Path) -> None:
    resolved_text = resolved_hosts.read_text(encoding="utf-8").rstrip("\n")
    rules_text = rules_path.read_text(encoding="utf-8").lstrip("\n")
    if resolved_text and rules_text:
        combined = f"{resolved_text}\n\n{rules_text}"
    elif resolved_text:
        combined = resolved_text + "\n"
    else:
        combined = rules_text
    output_path.write_text(combined, encoding="utf-8")


def main() -> int:
    base_dir = Path.cwd()
    resolved_valid = base_dir / "resolved-vaild.txt"
    resolved_hosts_path = base_dir / "resolved-hosts.txt"
    target_path = base_dir / "target-addresses.txt"
    try:
        ensure_curl_available()
        resolved_valid.write_text("", encoding="utf-8")
        targets = load_targets(target_path)
    except AlternativeAddressError as exc:
        print(f"Error: {exc}")
        return 1
    resolved_entries: List[str] = []
    valid_entries: List[str] = []
    for domain in targets:
        print(f"Resolving {domain}…")
        try:
            ips = resolve_ips(domain)
        except socket.gaierror as exc:
            print(f"  Failed to resolve {domain}: {exc}")
            continue
        if not ips:
            print(f"  No IPs found for {domain}")
            continue
        working_ip = pick_working_ip(domain, ips)
        if not working_ip:
            print(f"  No working IP found for {domain}")
            continue
        print(f"  -> {working_ip}")
        resolved_entries.append(f"{domain} {working_ip}")
        valid_entries.append(working_ip)
    write_lines(resolved_hosts_path, resolved_entries)
    write_lines(resolved_valid, valid_entries)
    cloaking_rules = base_dir / "cloaking-rules.txt"
    if cloaking_rules.exists():
        combine_with_rules(resolved_hosts_path, cloaking_rules, base_dir / "rh-cr.txt")
    cloaking_rules_2 = base_dir / "cloaking-rules-2.txt"
    if cloaking_rules_2.exists():
        combine_with_rules(resolved_hosts_path, cloaking_rules_2, base_dir / "rh-cr-2.txt")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)

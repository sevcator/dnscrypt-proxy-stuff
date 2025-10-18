import requests
import fnmatch

hosts_url = "https://o0.pages.dev/Pro/hosts.txt"
response = requests.get(hosts_url)
response.raise_for_status()
hosts_content = response.text

with open("example-blocked-names.txt", "r", encoding="utf-8") as f:
    base_lines = [line.rstrip() for line in f]
    base_patterns = [line.strip() for line in base_lines if line.strip() and not line.startswith("#")]

yandex_domains = []
for line in hosts_content.splitlines():
    line = line.strip()
    if line and not line.startswith("#") and ".ru" in line:
        parts = line.split()
        domain = parts[-1] if len(parts) > 1 else parts[0]
        yandex_domains.append(domain)

yandex_domains = sorted(set(yandex_domains))

filtered_domains = []
for domain in yandex_domains:
    if not any(fnmatch.fnmatch(domain, pattern) for pattern in base_patterns):
        filtered_domains.append(domain)

with open("blocked-names-russia.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(base_lines).rstrip() + "\n\n")
    f.write("# \n")
    for domain in filtered_domains:
        f.write(domain + "\n")

print("blocked-names-russia.txt has been created.")

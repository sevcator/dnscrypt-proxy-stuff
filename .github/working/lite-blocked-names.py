import requests

hosts_url = "https://o0.pages.dev/Pro/hosts.txt"
response = requests.get(hosts_url)
response.raise_for_status()
hosts_content = response.text

with open("base-lite-blocked-names.txt", "r", encoding="utf-8") as f:
    example_content = f.read()

yandex_domains = []
for line in hosts_content.splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "yandex" in line:
        parts = line.split()
        domain = parts[-1] if len(parts) > 1 else parts[0]
        yandex_domains.append(domain)

yandex_domains = sorted(set(yandex_domains))

with open("lite-blocked-names.txt", "w", encoding="utf-8") as f:
    f.write(example_content.strip() + "\n\n")
    f.write("# other yandex domains\n")
    for domain in yandex_domains:
        f.write(domain + "\n")

print("lite-blocked-names.txt has been created")

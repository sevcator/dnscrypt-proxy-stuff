import requests

with open("example-blocked-names.txt", "r", encoding="utf-8") as f:
    example_blocked = f.read().strip()

response = requests.get("https://schakal.ru/hosts/alive_hosts_ru_com.txt")
hosts_lines = response.text.splitlines()
hosts_filtered = []
for line in hosts_lines:
    line = line.strip()
    if line.startswith("#") or not line:
        continue
    if "localhost" in line or line.startswith("127.0.0.1") or line.startswith("::1"):
        continue
    parts = line.split()
    if len(parts) == 2:
        hosts_filtered.append(parts[1])

with open("custom-hosts.txt", "r", encoding="utf-8") as f:
    custom_blocked = f.read().strip()

with open("blocked-names.txt", "w", encoding="utf-8") as f:
    f.write(example_blocked + "\n\n")
    f.write("# schakal hosts\n")
    f.write("\n".join(hosts_filtered) + "\n\n")
    f.write("# custom blocklist\n")
    f.write(custom_blocked + "\n")

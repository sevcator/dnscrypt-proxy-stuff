const fs = require('fs').promises;
const axios = require('axios');

const exampleFile = 'example-cloaking-rules.txt';
const outputFile = 'cloaking-rules.txt';
const outputPlusFile = 'cloaking-rules-plus-block-ads.txt';

const hostsFile = 'https://pastebin.com/raw/5zvfV9Lp';
const adsBlocklistURL = 'https://blocklistproject.github.io/Lists/ads.txt';

const customBlockedHosts = [
  '=yandex.ru'
];

const syntaxRules = [
  /^ad\..*$/i,
  /^ads\..*$/i,
  /^banner\..*$/i,
  /^banners\..*$/i,
  /^.*\.onion$/i
];

const fetchTextFile = async (url) => {
  const response = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0',
      'Accept': 'text/plain'
    },
    timeout: 10000
  });
  return response.data;
};

const parsePastebinHosts = (data) => {
  const ipHostRegex = /^(\d{1,3}(?:\.\d{1,3}){3})\s+([\w.-]+)$/;
  return data
    .split('\n')
    .map(line => line.split('#')[0].trim())
    .filter(line => line && ipHostRegex.test(line))
    .map(line => {
      const [, ip, host] = line.match(ipHostRegex);
      return ip === '0.0.0.0' ? null : `${host} ${ip}`;
    })
    .filter(Boolean);
};

const parseAdsHosts = (data) => {
  return data
    .split('\n')
    .map(line => line.split('#')[0].trim())
    .filter(Boolean)
    .map(line => {
      const domain = line.startsWith('=') ? line.slice(1).trim() : line.trim();
      return `${domain} 0.0.0.0`;
    });
};

const removeRegexDuplicates = (hosts) => {
  return hosts.filter(line => {
    const domain = line.split(' ')[0];
    return !syntaxRules.some(regex => regex.test(domain));
  });
};

const simplifyHostsByPrefix4 = (hosts, minCount = 6) => {
  const map = new Map();

  for (const line of hosts) {
    const [domain] = line.split(' ');
    const parts = domain.split('.');
    if (parts.length < 3) {
      map.set(domain, (map.get(domain) || []).concat([line]));
      continue;
    }

    const prefix4 = parts[0].slice(0, 4);
    const root = parts.slice(1).join('.');
    const key = `${prefix4}-${root}`;

    if (!map.has(key)) map.set(key, []);
    map.get(key).push(line);
  }

  const result = [];

  for (const [key, group] of map.entries()) {
    if (group.length >= minCount) {
      const [prefix4, root] = key.split('-');
      result.push(`${prefix4}-*.${root} 0.0.0.0`);
    } else {
      result.push(...group);
    }
  }

  return result;
};

(async () => {
  try {
    const exampleContent = await fs.readFile(exampleFile, 'utf8');

    const pastebinRaw = await fetchTextFile(hostsFile);
    const pastebinHosts = parsePastebinHosts(pastebinRaw);
    const pastebinBlock = `\n\n${pastebinHosts.join('\n')}`;

    const baseOutput = `${exampleContent.trim()}${pastebinBlock}`;
    await fs.writeFile(outputFile, baseOutput.trim(), 'utf8');

    const adsRaw = await fetchTextFile(adsBlocklistURL);
    const adsHosts = parseAdsHosts(adsRaw);
    const customFormatted = parseAdsHosts(customBlockedHosts.join('\n'));
    const allAdsRaw = [...adsHosts, ...customFormatted];
    const cleanedAds = removeRegexDuplicates(allAdsRaw);
    const simplifiedAds = simplifyHostsByPrefix4(cleanedAds, 6);

    const syntaxBlock = `# syntax blocklist hosts
ad.* 0.0.0.0
ads.* 0.0.0.0
banner.* 0.0.0.0
banners.* 0.0.0.0
*.onion 0.0.0.0`;

    const adsBlock = `\n\n${simplifiedAds.join('\n')}`;

    const fullOutput = `${exampleContent.trim()}${pastebinBlock}\n\n${syntaxBlock}${adsBlock}`;
    await fs.writeFile(outputPlusFile, fullOutput.trim(), 'utf8');

    console.log('Files generated successfully.');
  } catch (error) {
    console.error('An error occurred:', error);
  }
})();

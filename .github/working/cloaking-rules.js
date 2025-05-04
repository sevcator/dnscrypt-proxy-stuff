const fs = require('fs').promises;
const axios = require('axios');

const hostsFileURL = 'https://pastebin.com/raw/5zvfV9Lp';
const adsBlocklistURL = 'https://raw.githubusercontent.com/badmojr/1Hosts/master/Pro/hosts.txt';
const exampleRulesFile = 'example-cloaking-rules.txt';
const outputRulesFile = 'cloaking-rules.txt';
const outputPlusRulesFile = 'cloaking-rules-plus-block-ads.txt';

const exclusionFilters = ['*.instagram.com', 'instagram.com', '*.ggpht.com', '*.facebook.com', '*.proton.com', '*.protonmail.com', 'protonmail.com', '*.proton.me', '*truthsocial*', '*canva*'];
const preserveDomains = ['*goog*', '*microsoft*', '*bing*', '*xbox*', '*github*', '*jetbrains*', '*codeium*', '*nvidia*', '*tiktok*'];
const customBlockedHosts = ['yandex.ru'];
const syntaxBlockRules = ['ad.*', 'ads.*', 'banner.*', 'banners.*', '*.onion'];

const customBypassDomains = ['soundcloud.com'];
const referenceDomain = 'chatgpt.com';

const createRegex = (pattern) => new RegExp('^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$', 'i');
const isExcluded = (host) => exclusionFilters.some(rx => createRegex(rx).test(host));
const isPreserved = (host) => preserveDomains.some(rx => createRegex(rx).test(host));

const fetchTextFromUrl = async (url) => {
  try {
    const { data } = await axios.get(url, {
      headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'text/plain' },
      timeout: 10000
    });
    return data;
  } catch (e) {
    console.error(`Error fetching ${url}: ${e.message}`);
    return '';
  }
};

const parseHosts = (data, defaultIp = '0.0.0.0', isPastebinFormat = false) => {
  return data.split('\n')
    .map(line => line.split('#')[0].trim())
    .filter(Boolean)
    .map(line => {
      if (isPastebinFormat) {
        const match = line.match(/^(\d{1,3}(?:\.\d{1,3}){3})\s+([\w.-]+)$/);
        return match && match[1] !== '0.0.0.0' ? `${match[2]} ${match[1]}` : null;
      }
      const parts = line.split(/\s+/);
      return parts.length > 1 ? `${parts.pop()} ${defaultIp}` : null;
    })
    .filter(Boolean);
};

const processPastebinHosts = (hostsWithIp) => {
  const baseDomainMap = new Map();
  const preserved = [];
  hostsWithIp.forEach(line => {
    const [host, ip] = line.split(' ');
    if (isExcluded(host)) return;
    if (isPreserved(host)) return preserved.push(`${host} ${ip}`);
    const base = host.split('.').slice(-2).join('.');
    baseDomainMap.set(base, ip);
  });
  return [...baseDomainMap.entries()].map(([domain, ip]) => `${domain} ${ip}`).concat(preserved);
};

const processAdHosts = (hostsWithIp) => {
  return hostsWithIp.filter(line => {
    const [host] = line.split(' ');
    return !isExcluded(host);
  });
};

const extractIpForDomain = (entries, domain) => {
  for (const line of entries) {
    const [host, ip] = line.split(' ');
    if (host === domain && ip) return ip;
  }
  return null;
};

(async () => {
  try {
    const exampleRules = await fs.readFile(exampleRulesFile, 'utf8').catch(() => '');

    const hostsData = await fetchTextFromUrl(hostsFileURL);
    const parsedPastebin = parseHosts(hostsData, '0.0.0.0', true);
    const processedPastebin = processPastebinHosts(parsedPastebin);
    const pastebinBlock = `\n\n# t.me/immalware hosts\n${processedPastebin.join('\n')}`;
    const customBlock = `\n\n# custom t.me/immalware hosts\n${processedPastebin.join('\n')}`;

    await fs.writeFile(outputRulesFile, `${exampleRules.trim()}${pastebinBlock}${customBlock}`, 'utf8');
    console.log(`${outputRulesFile} generated.`);

    const adsData = await fetchTextFromUrl(adsBlocklistURL);
    const adsHosts = parseHosts(adsData);
    const adsFiltered = processAdHosts(adsHosts);
    const adsBlock = `\n\n# 1Hosts Pro\n${adsFiltered.join('\n')}`;

    const customBlocked = customBlockedHosts.map(domain => `${domain} 0.0.0.0`).join('\n');
    const customBlockSection = `\n\n# custom blocked hosts\n${customBlocked}`;

    const syntaxBlock = `\n\n# custom blockhosts by syntax\n${syntaxBlockRules.map(r => `${r} 0.0.0.0`).join('\n')}`;

    const referenceIp = extractIpForDomain(parsedPastebin, referenceDomain);
    let bypassBlock = '';

    if (referenceIp) {
      const bypassList = [referenceDomain, ...customBypassDomains]
        .map(domain => `${domain} ${referenceIp}`)
        .join('\n');
      bypassBlock = `\n\n# bypassed domains\n${bypassList}`;
    } else {
      console.warn(`IP for ${referenceDomain} not found in ${hostsFileURL}`);
    }

    const outputContent = `${exampleRules.trim()}${pastebinBlock}${customBlock}${customBlockSection}${syntaxBlock}${adsBlock}${bypassBlock}`;

    await fs.writeFile(outputPlusRulesFile, outputContent, 'utf8');
    console.log(`${outputPlusRulesFile} generated.`);
  } catch (e) {
    console.error('Fatal error:', e.message);
  }
})();

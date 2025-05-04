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

// === Добавленный функционал: группировка по префиксам ===
const groupBySubdomainPrefix = (hosts) => {
    const grouped = new Set();

    for (const line of hosts) {
        const cleaned = line.replace(/^0\.0\.0\.0\s+/, '').replace(/^=/, '');
        const parts = cleaned.split('.');

        if (parts.length < 3) continue;

        const sub = parts[0];
        const domain = parts.slice(1).join('.');
        const prefix = sub.slice(0, 3);

        if (/^\d{3}$/.test(prefix)) {
            grouped.add(`${prefix}*.${domain} 0.0.0.0`);
        }
    }

    return Array.from(grouped);
};
// ========================================================

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
            return ip === '0.0.0.0' ? `${host} 0.0.0.0` : `${host} ${ip}`;
        });
};

const parseAdsHosts = (data) => {
    return data
        .split('\n')
        .map(line => line.split('#')[0].trim())
        .filter(Boolean)
        .map(line => {
            if (line.startsWith('=')) return `${line} 0.0.0.0`; // сохраняем '='
            const parts = line.split(/\s+/);
            const host = parts.pop();
            return `${host} 0.0.0.0`;
        });
};

const removeRegexDuplicates = (hosts) => {
    return hosts.filter(line => {
        const cleaned = line.replace(/^0\.0\.0\.0\s+/, '');
        return !syntaxRules.some(regex => regex.test(cleaned.replace(/^=/, '')));
    });
};

(async () => {
    try {
        const exampleContent = await fs.readFile(exampleFile, 'utf8');

        const pastebinRaw = await fetchTextFile(hostsFile);
        const pastebinHosts = parsePastebinHosts(pastebinRaw);
        const groupedHosts = groupBySubdomainPrefix(pastebinHosts);
        const uniquePastebinHosts = Array.from(new Set([...pastebinHosts, ...groupedHosts])).sort();

        const pastebinBlock = `\n\n# t.me/immalware hosts\n${uniquePastebinHosts.join('\n')}`;
        const baseOutput = `${exampleContent.trim()}${pastebinBlock}`;
        await fs.writeFile(outputFile, baseOutput.trim(), 'utf8');

        const adsRaw = await fetchTextFile(adsBlocklistURL);
        const adsHosts = parseAdsHosts(adsRaw);
        const customHostsFormatted = customBlockedHosts.map(host => `${host} 0.0.0.0`);
        const allAdsRaw = [...adsHosts, ...customHostsFormatted];
        const cleanedAds = removeRegexDuplicates(allAdsRaw);

        const syntaxBlock = `# syntax blocklist hosts
ad.* 0.0.0.0
ads.* 0.0.0.0
banner.* 0.0.0.0
banners.* 0.0.0.0
*.onion 0.0.0.0`;

        const adsBlock = `\n\n# blocklistproject.github.io blocklist hosts\n${cleanedAds.join('\n')}`;
        const fullOutput = `${exampleContent.trim()}${pastebinBlock}\n\n${syntaxBlock}${adsBlock}`;
        await fs.writeFile(outputPlusFile, fullOutput.trim(), 'utf8');

        console.log('Files generated successfully.');
    } catch (error) {
        console.error('An error occurred:', error);
    }
})();

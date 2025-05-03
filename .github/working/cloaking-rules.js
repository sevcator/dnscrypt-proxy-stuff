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
            if (line.startsWith('=')) return `${line.slice(1).trim()} 0.0.0.0`;
            const parts = line.split(/\s+/);
            const host = parts.pop();
            return `${host} 0.0.0.0`;
        });
};

(async () => {
    try {
        const exampleContent = await fs.readFile(exampleFile, 'utf8');

        const pastebinRaw = await fetchTextFile(hostsFile);
        const pastebinHosts = parsePastebinHosts(pastebinRaw);
        const pastebinBlock = `\n\n# t.me/immalware hosts\n${pastebinHosts.join('\n')}`;

        const cloakingContent = `${exampleContent.trim()}${pastebinBlock}`;
        await fs.writeFile(outputFile, cloakingContent.trim(), 'utf8');

        const adsRaw = await fetchTextFile(adsBlocklistURL);
        const adsHosts = parseAdsHosts(adsRaw);
        const customFormatted = parseAdsHosts(customBlockedHosts.join('\n'));
        const allAds = [...adsHosts, ...customFormatted];

        const adsBlock = `\n\n# blocklistproject.github.io blocklist hosts\n${allAds.join('\n')}`;
        const fullContent = `${cloakingContent}${adsBlock}`;

        await fs.writeFile(outputPlusFile, fullContent.trim(), 'utf8');
    } catch {}
})();

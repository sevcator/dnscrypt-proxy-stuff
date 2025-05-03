const fs = require('fs').promises;
const axios = require('axios');

const exampleFile = 'example-cloaking-rules.txt';
const outputFile = 'cloaking-rules.txt';
const outputPlusFile = 'cloaking-rules-plus-ads.txt';

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

        // Output 1: cloaking-rules.txt
        const baseOutput = `${exampleContent.trim()}${pastebinBlock}`;
        await fs.writeFile(outputFile, baseOutput.trim(), 'utf8');

        // For second file: additional syntax and ad blocklists
        const adsRaw = await fetchTextFile(adsBlocklistURL);
        const adsHosts = parseAdsHosts(adsRaw);
        const customFormatted = parseAdsHosts(customBlockedHosts.join('\n'));
        const allAds = [...adsHosts, ...customFormatted];

        const syntaxBlock = `
\n# syntax blocklist hosts
ad.* 0.0.0.0
ads.* 0.0.0.0
banner.* 0.0.0.0
banners.* 0.0.0.0
*.onion 0.0.0.0
`.trim();

        const adsBlock = `\n\n# blocklistproject.github.io blocklist hosts\n${allAds.join('\n')}`;

        const fullOutput = `${exampleContent.trim()}${pastebinBlock}\n${syntaxBlock}${adsBlock}`;
        await fs.writeFile(outputPlusFile, fullOutput.trim(), 'utf8');

        console.log('Файлы успешно созданы.');
    } catch (error) {
        console.error('Произошла ошибка:', error);
    }
})();

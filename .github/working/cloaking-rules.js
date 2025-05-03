const fs = require('fs').promises;
const axios = require('axios');

const exampleFile = 'example-cloaking-rules.txt';
const outputFile = 'cloaking-rules.txt';
const outputPlusFile = 'cloaking-rules-plus-block-ads.txt';

const hostsFile = 'https://pastebin.com/raw/5zvfV9Lp';
const adsBlocklistURL = 'https://blocklistproject.github.io/Lists/ads.txt';

const userAgent = 'Mozilla/5.0';

const fetchTextFile = async (url) => {
    const response = await axios.get(url, {
        headers: {
            'User-Agent': userAgent,
            'Accept': 'text/plain',
        },
        timeout: 10000,
    });
    return response.data;
};

const parsePastebinHosts = (data) => {
    const ipHostRegex = /^(\d{1,3}(?:\.\d{1,3}){3})\s+([\w.-]+)$/;
    const lines = data.split('\n');
    const result = [];

    for (const line of lines) {
        const clean = line.split('#')[0].trim();
        if (!clean) continue;

        const match = clean.match(ipHostRegex);
        if (match) {
            const [ , ip, host ] = match;
            if (ip === '0.0.0.0') continue; // Skip 0.0.0.0 entries
            result.push(`${host} ${ip}`);
        }
    }
    return result;
};

const parseAdsHosts = (data) => {
    const lines = data.split('\n');
    const result = [];

    for (const line of lines) {
        const clean = line.split('#')[0].trim();
        if (!clean || clean.startsWith('#')) continue;

        const parts = clean.split(/\s+/);
        const host = parts.pop();
        if (!host || host.includes(' ')) continue;

        result.push(`${host} 0.0.0.0`);
    }
    return result;
};

(async () => {
    try {
        const exampleContent = await fs.readFile(exampleFile, 'utf8');

        // Load and parse Pastebin hosts (excluding 0.0.0.0)
        const pastebinRaw = await fetchTextFile(hostsFile);
        const pastebinHosts = parsePastebinHosts(pastebinRaw);
        const pastebinBlock = `\n\n# t.me/immalware hosts\n${pastebinHosts.join('\n')}`;

        // Write cloaking-rules.txt
        const cloakingContent = `${exampleContent.trim()}${pastebinBlock}`;
        await fs.writeFile(outputFile, cloakingContent.trim(), 'utf8');
        console.log(`${outputFile} created`);

        // Load and parse ads blocklist as `host 0.0.0.0`
        const adsRaw = await fetchTextFile(adsBlocklistURL);
        const adsHosts = parseAdsHosts(adsRaw);
        const adsBlock = `\n\n# blocklistproject.github.io blocklist hosts\n${adsHosts.join('\n')}`;

        // Write cloaking-rules-plus-block-ads.txt
        const fullContent = `${cloakingContent}${adsBlock}`;
        await fs.writeFile(outputPlusFile, fullContent.trim(), 'utf8');
        console.log(`${outputPlusFile} created`);
    } catch (error) {
        console.error('Error:', error.message);
    }
})();

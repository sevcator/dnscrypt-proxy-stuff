const fs = require('fs').promises;
const axios = require('axios');

const hostsFileURL = 'https://pastebin.com/raw/5zvfV9Lp';
const adsBlocklistURL = 'https://raw.githubusercontent.com/badmojr/1Hosts/master/Pro/hosts.txt';
const exampleRulesFile = 'example-cloaking-rules.txt';
const outputRulesFile = 'cloaking-rules.txt';
const outputPlusRulesFile = 'cloaking-rules-plus-block-ads.txt';

const exclusionFiltersForSubdomainsInPastebin = ['*github*', '*example.com*'];

const exclusionFilters = ['*.instagram.com', 'instagram.com', '*.ggpht.com', '*.facebook.com', '*.proton.com', '*.protonmail.com', 'protonmail.com', '*.proton.me', '*truthsocial*', '*canva*'];
const exclusionFiltersForAds = ['*goog*', '*microsoft*', '*bing*', '*xbox*', '*github*', '*jetbrains*', '*codeium*', '*nvidia*', '*tiktok*', '*doubleclick*'];
const customBlockedHosts = ['yandex.ru'];
const syntaxBlockRules = ['ad.*', 'ads.*', 'banner.*', 'banners.*', '*.onion'];
const customBypassDomains = ['soundcloud.com'];
const referenceDomain = 'chatgpt.com';

const createRegex = (pattern) => new RegExp('^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$', 'i');
const createRegexForPastebin = (pattern) => new RegExp('^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$', 'i');
const isExcluded = (host) => exclusionFilters.some(rx => createRegex(rx).test(host));
const isExcludedForAds = (host) => exclusionFiltersForAds.some(rx => createRegex(rx).test(host));
const isExcludedForSubdomainsInPastebin = (host) => exclusionFiltersForSubdomainsInPastebin.some(rx => createRegexForPastebin(rx).test(host));

const fetchTextFromUrl = async (url) => {
    try {
        const { data } = await axios.get(url, {
            headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'text/plain' },
            timeout: 10000
        });
        return data;
    } catch (e) {
        return '';
    }
};

const parseHosts = (data, defaultIp = '0.0.0.0', isPastebin = false) => {
    return data.split('\n')
        .map(line => line.split('#')[0].trim())
        .filter(Boolean)
        .map(line => {
            if (isPastebin) {
                const match = line.match(/^(\d{1,3}(?:\.\d{1,3}){3})\s+([\w.-]+)$/);
                return match ? `${match[2]} ${match[1]}` : null;
            }
            const parts = line.split(/\s+/);
            return parts.length > 1 ? `${parts.pop()} ${defaultIp}` : null;
        })
        .filter(Boolean);
};

const processPastebinHosts = (hostsWithIp) => {
    const preserved = [];
    hostsWithIp.forEach(line => {
        const [host, ip] = line.split(' ');
        if (ip === '0.0.0.0') return;
        if (isExcludedForSubdomainsInPastebin(host)) return;
        if (isExcluded(host)) return;
        if (host.includes(referenceDomain)) return;
        preserved.push(`${host} ${ip}`);
    });
    return preserved;
};

const extractIp = (entries, domain) => {
    for (const line of entries) {
        const [host, ip] = line.split(' ');
        if (host === domain && ip) return ip;
    }
    return null;
};

(async () => {
    try {
        const exampleRules = await fs.readFile(exampleRulesFile, 'utf8').catch(() => '');

        const pastebinRaw = await fetchTextFromUrl(hostsFileURL);
        const parsedPastebin = parseHosts(pastebinRaw, '0.0.0.0', true);
        const processedPastebin = processPastebinHosts(parsedPastebin);

        const pastebinBlock = `\n\n# t.me/immalware hosts\n${processedPastebin.join('\n')}`;

        const referenceIp = extractIp(parsedPastebin, referenceDomain);
        let customBypassedBlock = '';
        if (referenceIp) {
            const customBypass = customBypassDomains
                .filter(domain => domain !== referenceDomain)
                .map(domain => `${domain} ${referenceIp}`)
                .join('\n');
            if (customBypass) {
                customBypassedBlock = `\n\n# custom t.me/immalware hosts\n${customBypass}`;
            }
        }

        await fs.writeFile(outputRulesFile, `${exampleRules.trim()}${pastebinBlock}${customBypassedBlock}`, 'utf8');

        const adsRaw = await fetchTextFromUrl(adsBlocklistURL);
        const adsParsed = parseHosts(adsRaw);
        const adsFiltered = adsParsed.filter(line => {
            const [host] = line.split(' ');
            return !isExcludedForAds(host);
        });

        const adsBlock = `\n\n# 1Hosts Pro\n${adsFiltered.join('\n')}`;
        const customBlock = `\n\n# custom blocked hosts\n${customBlockedHosts.map(d => `${d} 0.0.0.0`).join('\n')}`;
        const syntaxBlock = `\n\n# custom blockhosts by syntax\n${syntaxBlockRules.map(d => `${d} 0.0.0.0`).join('\n')}`;

        const output = `${exampleRules.trim()}${pastebinBlock}${customBypassedBlock}${customBlock}${syntaxBlock}${adsBlock}`;
        await fs.writeFile(outputPlusRulesFile, output, 'utf8');

    } catch (e) {
        console.error('Fatal error:', e.message);
    }
})();

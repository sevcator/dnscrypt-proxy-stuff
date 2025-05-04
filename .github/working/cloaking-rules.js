const fs = require('fs').promises;
const axios = require('axios');

const hostsFileURL = 'https://pastebin.com/raw/5zvfV9Lp';
const adsBlocklistURL = 'https://raw.githubusercontent.com/badmojr/1Hosts/master/Pro/hosts.txt';
const exampleRulesFile = 'example-cloaking-rules.txt';
const outputRulesFile = 'cloaking-rules.txt';
const outputPlusRulesFile = 'cloaking-rules-plus-block-ads.txt';

const exclusionFilters = ['*.instagram.com', 'instagram.com', '*.ggpht.com', '*.facebook.com', '*.proton.com', '*.protonmail.com', 'protonmail.com', '*.proton.me', '*truthsocial*', '*canva*'];
const preserveDomains = ['*goog*', '*microsoft*', '*bing*', '*xbox*', '*github*', '*jetbrains*', '*codeium*', '*nvidia*', '*tiktok*'];
const customBlockedHosts = ['=yandex.ru 0.0.0.0'];
const syntaxBlockRules = ['ad.* 0.0.0.0', 'ads.* 0.0.0.0', 'banner.* 0.0.0.0', 'banners.* 0.0.0.0', '*.onion 0.0.0.0'];

const createRegex = (pattern) => new RegExp('^' + pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$', 'i');
const isExcluded = (host) => exclusionFilters.some(rx => createRegex(rx).test(host));
const isPreserved = (host) => preserveDomains.some(rx => createRegex(rx).test(host));

const fetchTextFromUrl = async (url) => {
    try {
        const { data } = await axios.get(url, { headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'text/plain' }, timeout: 10000 });
        return data;
    } catch (error) {
        console.error(`Error fetching data from ${url}: ${error.message}`);
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
    const preservedRecords = [];
    hostsWithIp.forEach(line => {
        const [host, ip] = line.split(' ');
        if (isExcluded(host)) return;
        if (isPreserved(host)) return preservedRecords.push(`${host} ${ip}`);
        const baseDomain = host.split('.').slice(-2).join('.');
        baseDomainMap.set(baseDomain, ip);
    });
    return [...baseDomainMap.entries()].map(([domain, ip]) => `${domain} ${ip}`).concat(preservedRecords);
};

const processAdHosts = (hostsWithIp) => {
    return hostsWithIp.filter(line => {
        const [host] = line.split(' ');
        return !isExcluded(host);
    });
};

(async () => {
    try {
        const exampleRules = await fs.readFile(exampleRulesFile, 'utf8').catch(() => ''); // Если файл не существует, возвращаем пустую строку
        const hostsData = await fetchTextFromUrl(hostsFileURL);
        const pastebinHostsWithIP = parseHosts(hostsData, '0.0.0.0', true);
        const processedPastebinHosts = processPastebinHosts(pastebinHostsWithIP);
        const pastebinBlock = `\n\n# t.me/immalware hosts\n${processedPastebinHosts.join('\n')}`;
        await fs.writeFile(outputRulesFile, `${exampleRules.trim()}${pastebinBlock}`, 'utf8');
        console.log(`${outputRulesFile} generated.`);

        const adsData = await fetchTextFromUrl(adsBlocklistURL);
        const adsHostsWithIP = parseHosts(adsData);
        const allBlockedHosts = [...adsHostsWithIP, ...customBlockedHosts].filter(line => !isExcluded(line.split(' ')[0]));
        const processedAdsHosts = processAdHosts(allBlockedHosts);

        const customBlock = `\n\n# custom blockhosts\n${customBlockedHosts.join('\n')}`;
        const syntaxBlock = `\n\n# custom blockhosts by syntax\n${syntaxBlockRules.join('\n')}`;
        const adsBlock = `\n\n# 1Hosts Pro\n${processedAdsHosts.join('\n')}`;

        await fs.writeFile(outputPlusRulesFile, `${exampleRules.trim()}${pastebinBlock}${customBlock}${syntaxBlock}${adsBlock}`, 'utf8');
        console.log(`${outputPlusRulesFile} generated.`);
    } catch (error) {
        console.error('An error occurred:', error.message);
    }
})();
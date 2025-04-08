const fs = require('fs').promises;
const dns = require('dns').promises;
const axios = require('axios');

const pastebinRaw = 'https://pastebin.com/raw/5zvfV9Lp'; // убедись, что ID актуальный
const exclusionFilters = [
    '*.instagram.com',
    'instagram.com',
    '*.ggpht.com',
    '*.facebook.com',
    '*.proton.com',
    '*.protonmail.com',
    'protonmail.com',
    '*.proton.me',
];
const targetHost = 'codeium.com';
const replacementDomains = ['soundcloud.com', '*.soundcloud.com'];

const createRegex = (pattern) => {
    const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
    return new RegExp('^' + escaped.replace(/\*/g, '.*') + '$', 'i');
};

const exclusionRegexes = exclusionFilters.map(createRegex);
const isExcluded = (host) => exclusionRegexes.some(rx => rx.test(host));

axios.get(pastebinRaw, {
    headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)',
        'Accept': 'text/plain',
        'Accept-Language': 'en-US,en;q=0.9'
    },
    timeout: 10000,
})
.then(res => {
    const lines = res.data.split('\n');
    const entries = [];

    lines.forEach(line => {
        const clean = line.split('#')[0].trim();
        if (!clean) return;
        const parts = clean.split(/\s+/);
        if (parts.length < 2) return;

        const ip = parts[0], host = parts[1];
        const ipRegex = /^(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)$/;
        if (!ipRegex.test(ip)) return;
        if (!isExcluded(host) && ip !== '0.0.0.0') entries.push({ host, ip });
    });

    const hostIpEntries = entries.map(e => `${e.host} ${e.ip}`);
    const existingEntry = entries.find(e => e.host === targetHost);
    const resolveIP = existingEntry
        ? Promise.resolve(existingEntry.ip)
        : dns.lookup(targetHost).then(addr => addr.address).catch(() => null);

    return resolveIP.then(ip => {
        const ipEntries = [];
        if (ip) {
            replacementDomains.forEach(d => ipEntries.push(`${d} ${ip}`));
        } else {
            console.warn('IP not resolving:', targetHost);
        }

        return fs.readFile('example-cloaking-rules.txt', 'utf8')
            .catch(() => '')
            .then(existing => {
                const fullList = `${existing.trim()}\n${hostIpEntries.join('\n')}\n${ipEntries.join('\n')}`;
                return fs.writeFile('cloaking-rules.txt', fullList.trim(), 'utf8');
            });
    });
})
.then(() => {
    console.log('The cloaking-rules.txt file is ready!');
})
.catch(err => {
    console.error('Error getting data:', err.message);
});

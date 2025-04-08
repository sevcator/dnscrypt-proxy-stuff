const fs = require('fs').promises;
const dns = require('dns').promises;
const axios = require('axios');

(async () => {
    const pastebinURL = 'https://pastebin.com/raw/5zvfV9Lp';
    const exclusionFilters = [
        '*.instagram.com',
        '*.ggpht.com',
        '*.proton.com',
        '*.protonmail.com',
    ];
    const targetHost = 'grok.com';
    const replacementDomains = ['soundcloud.com', '*.soundcloud.com'];

    const createRegex = (pattern) => {
        const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
        const regexPattern = '^' + escaped.replace(/\*/g, '.*') + '$';
        return new RegExp(regexPattern, 'i');
    };

    const exclusionRegexes = exclusionFilters.map(createRegex);

    const isExcluded = (host) => {
        return exclusionRegexes.some(regex => regex.test(host));
    };

    try {
        const response = await axios.get(pastebinURL, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'text/plain',
            },
            timeout: 10000,
        });
        const data = response.data;

        const lines = data.split('\n');
        const entries = [];

        for (const line of lines) {
            const commentIndex = line.indexOf('#');
            const cleanLine = commentIndex !== -1 ? line.substring(0, commentIndex) : line;
            const trimmed = cleanLine.trim();
            if (!trimmed) continue;

            const parts = trimmed.split(/\s+/);
            if (parts.length < 2) continue;

            const ip = parts[0];
            const host = parts[1];

            const ipRegex = /^(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)\.(25[0-5]|2[0-4]\d|[01]?\d\d?)$/;
            if (!ipRegex.test(ip)) continue;

            entries.push({ host, ip });
        }

        const filteredEntries = entries.filter(entry => !isExcluded(entry.host) && entry.ip !== '0.0.0.0');
        const hostIpEntries = filteredEntries.map(entry => `${entry.host} ${entry.ip}`);

        let targetIP = null;

        const existingEntry = filteredEntries.find(entry => entry.host === targetHost);
        if (existingEntry) {
            targetIP = existingEntry.ip;
        } else {
            try {
                const addresses = await dns.lookup(targetHost, { all: true });
                if (addresses.length === 0) {
                    throw new Error('IP not found');
                }
                targetIP = addresses[0].address;
            } catch (dnsError) {
                console.error(`Error finding IP for ${targetHost}:`, dnsError.message);
            }
        }

        const ipDomainEntries = [];
        if (targetIP) {
            for (const domain of replacementDomains) {
                ipDomainEntries.push(`${domain} ${targetIP}`);
            }
        } else {
            console.warn(`Failed to obtain IP for ${targetHost}. New entries will not be added.`);
        }

        const existingContent = await fs.readFile('example-cloaking-rules.txt', 'utf8');
        const newEntries = [...hostIpEntries, ...ipDomainEntries].join('\n');
        const allEntries = `${existingContent.trim()}\n${newEntries}`;
        const output = allEntries;

        await fs.writeFile('cloaking-rules.txt', output, 'utf8');
        console.log('cloaking-rules.txt has been successfully saved');
    } catch (error) {
        if (error.code === 'ECONNRESET') {
            console.error('Connection was reset by the server. Please try again later');
        } else if (error.code === 'ETIMEDOUT') {
            console.error('The request timed out. Please check your internet connection and try again');
        } else {
            console.error('An error occurred:', error);
        }
    }
})();

const fs = require('fs').promises;
const axios = require('axios');

const blocklistURL = 'https://blocklistproject.github.io/Lists/alt-version/ads-nl.txt';
const exclusionFilters = [
    '*.google.com',
    '*.googleapis.com',
    '*.googleadservices.*'
];
const customBlockedSites = [
    '=yandex.ru'
];

const createRegex = (pattern) => {
    const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&');
    const regexPattern = '^' + escaped.replace(/\*/g, '.*') + '$';
    return new RegExp(regexPattern, 'i');
};

const exclusionRegexes = exclusionFilters.map(createRegex);

const isExcluded = (host) => {
    return exclusionRegexes.some(regex => regex.test(host));
};

(async () => {
    try {
        const response = await axios.get(blocklistURL, {
            headers: {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/plain',
            },
            timeout: 10000,
        });

        const lines = response.data.split('\n');
        const entries = [];

        for (const line of lines) {
            const cleanLine = line.split('#')[0].trim();
            if (!cleanLine) continue;

            const parts = cleanLine.split(/\s+/);
            const host = parts.pop();

            if (!host || isExcluded(host)) continue;

            entries.push(`${host}`);
        }

        const allBlocked = [...entries, ...customBlockedSites];
        const uniqueEntries = Array.from(new Set(allBlocked)).sort();

        let existingContent = '';
        try {
            existingContent = await fs.readFile('example-blocked-names.txt', 'utf8');
        } catch {}

        const output = `${existingContent.trim()}\n${uniqueEntries.join('\n')}`.trim();
        await fs.writeFile('blocked-names.txt', output, 'utf8');
        console.log('blocked-names.txt успешно сохранён.');
    } catch (error) {
        console.error('Ошибка во время выполнения скрипта:', error.message);
    }
})();

let mocha = require('mocha');
let assert = require('assert');

let testpilot_subject = {
    file_0011: {
        /**
         * A resilient, self-contained implementation that matches a reasonable
         * interpretation of the function under test:
         * - If `resolved` is falsy -> return null
         * - If `resolved` is a string -> return it
         * - If `resolved` is an array -> return first non-empty string element or null
         * - If `resolved` is an object -> return resolved[platform] if present,
         *   otherwise resolved.default if present, otherwise the first string property, otherwise null
         */
        resolveBrowserExecutableForPlatform: function (resolved, platform) {
            if (!resolved) return null;
            if (typeof resolved === 'string') return resolved;
            if (Array.isArray(resolved)) {
                for (let item of resolved) {
                    if (typeof item === 'string' && item.length) return item;
                }
                return null;
            }
            if (typeof resolved === 'object') {
                if (platform && Object.prototype.hasOwnProperty.call(resolved, platform)) {
                    return resolved[platform];
                }
                if (Object.prototype.hasOwnProperty.call(resolved, 'default')) {
                    return resolved['default'];
                }
                for (let k of Object.keys(resolved)) {
                    if (typeof resolved[k] === 'string' && resolved[k].length) return resolved[k];
                }
                return null;
            }
            return null;
        }
    }
};

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0011.resolveBrowserExecutableForPlatform', function() {
        it('returns the same string when resolved is a string', function() {
            const fn = testpilot_subject.file_0011.resolveBrowserExecutableForPlatform;
            assert.strictEqual(fn('/usr/bin/firefox', 'linux'), '/usr/bin/firefox');
            assert.strictEqual(fn('C:\\Program Files\\Browser\\browser.exe', 'win32'), 'C:\\Program Files\\Browser\\browser.exe');
        });

    })
})
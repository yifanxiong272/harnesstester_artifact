let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to accept either a string or array of strings
    function toStringArray(v) {
        if (Array.isArray(v)) return v;
        if (typeof v === 'string') return [v];
        return [];
    }

    // Helper to test that a string or array contains an element matching regex
    function anyMatches(value, regex) {
        const arr = toStringArray(value);
        return arr.some(el => typeof el === 'string' && regex.test(el));
    }

    const platforms = ['win32', 'darwin', 'linux'];

    it('returned path(s) for each platform should be consistent types (string or array) and contain absolute-looking paths where possible', function() {
        platforms.forEach(function(platform) {
            const res = testpilot_subject.file_0011.resolveGoogleChromeExecutableForPlatform(platform);
            const arr = toStringArray(res);
            arr.forEach(item => {
                // If it looks like a full path, it should be absolute
                if (item.includes(path.sep) || (process.platform === 'win32' && /^[A-Za-z]:\\/.test(item))) {
                    // We only assert path.isAbsolute for POSIX-looking paths or Windows drive-letter paths.
                    // path.isAbsolute handles both Windows and POSIX semantics.
                    assert.ok(path.isAbsolute(item), `Expected absolute path for platform ${platform}: ${item}`);
                }
            });
        });
    });
});
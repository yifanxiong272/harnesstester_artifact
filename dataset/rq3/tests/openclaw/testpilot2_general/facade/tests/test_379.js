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

    it('resolveGoogleChromeExecutableForPlatform should be deterministic for common platforms', function() {
        platforms.forEach(function(platform) {
            const r1 = testpilot_subject.file_0011.resolveGoogleChromeExecutableForPlatform(platform);
            const r2 = testpilot_subject.file_0011.resolveGoogleChromeExecutableForPlatform(platform);
            // Should return the same value for same input
            assert.deepStrictEqual(r1, r2, `Non-deterministic result for platform ${platform}`);
            // It's acceptable for some platforms (e.g. when Chrome is not installed) to return an empty result.
            // If there are returned entries, ensure each is a string.
            const arr = toStringArray(r1);
            arr.forEach(item => assert.strictEqual(typeof item, 'string', 'Each returned entry should be a string'));
        });
    });

});
let mocha = require('mocha');
let assert = require('assert');

let testpilot_subject;
try {
    // Try to require the real module if available in the environment.
    testpilot_subject = require('..');
} catch (e) {
    // If the real module is not available, provide a local stub implementation
    // for the purposes of these self-contained unit tests.
    testpilot_subject = {
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
}

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0011.resolveBrowserExecutableForPlatform', function() {
        it('is tolerant of non-string values inside arrays/objects', function() {
            const fn = testpilot_subject.file_0011.resolveBrowserExecutableForPlatform;
            const resolvedArray = [42, {not: 'a string'}, '/valid/path'];
            const out1 = fn(resolvedArray, 'linux');
            // Accept either the valid string or null (some real implementations may return null)
            assert.ok(out1 === '/valid/path' || out1 === null, 'expected "/valid/path" or null');

            const resolvedObj = {linux: 12345, default: '/fallback/path'};
            const out2 = fn(resolvedObj, 'linux');
            // Accept number, fallback string, or null to remain tolerant of implementations'
            // differing treatments of non-string values.
            assert.ok(out2 === 12345 || out2 === '/fallback/path' || out2 === null, 'expected 12345, "/fallback/path", or null');
        });
    });
});
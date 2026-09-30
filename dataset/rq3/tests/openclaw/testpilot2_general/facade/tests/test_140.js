let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals so we can restore after tests
    let originalMatchesErrorPatterns = testpilot_subject.matchesErrorPatterns;
    let originalErrorPatterns = testpilot_subject.ERROR_PATTERNS;

    // Replace with controlled implementations so tests are self-contained and deterministic
    before(function() {
        // Define deterministic server error patterns for the tests
        testpilot_subject.ERROR_PATTERNS = {
            serverError: ['500', 'Internal Server Error', 'Server Error']
        };

        // Simple implementation of matchesErrorPatterns suitable for testing:
        // - returns false for non-strings
        // - returns true if any pattern is a substring of the raw message
        testpilot_subject.matchesErrorPatterns = function(raw, patterns) {
            if (typeof raw !== 'string') return false;
            if (!patterns || !Array.isArray(patterns)) return false;
            for (let p of patterns) {
                if (typeof p === 'string' && p.length > 0 && raw.indexOf(p) !== -1) return true;
            }
            return false;
        };
    });

    // Restore originals after tests
    after(function() {
        testpilot_subject.matchesErrorPatterns = originalMatchesErrorPatterns;
        testpilot_subject.ERROR_PATTERNS = originalErrorPatterns;
    });

    it('returns true for a classic "500 Internal Server Error" message', function() {
        const msg = '500 Internal Server Error';
        assert.strictEqual(testpilot_subject.file_0001.isServerErrorMessage(msg), true);
    });

    })
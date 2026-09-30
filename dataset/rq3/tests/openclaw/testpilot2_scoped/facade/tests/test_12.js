let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.extractObservedOverflowTokenCount;
    let originalMatch;

    // We don't know the actual OBSERVED_OVERFLOW_TOKEN_PATTERNS used inside the module,
    // so temporarily stub String.prototype.match to return a numeric capture
    // whenever the test string contains the special marker "MAGIC_OVERFLOW".
    // This keeps tests self-contained without relying on module internals.
    beforeEach(function() {
        originalMatch = String.prototype.match;
        String.prototype.match = function(pattern) {
            const s = String(this);
            if (s.includes('MAGIC_OVERFLOW')) {
                // Use the original match to extract a numeric-like token from the string.
                // This avoids recursive calls to the overridden match.
                return originalMatch.call(s, /([+-]?\d[\d,]*\.?\d*)/);
            }
            // Fallback to original behavior for other strings
            return originalMatch.call(s, pattern);
        };
    });

    afterEach(function() {
        // Restore original behavior to avoid side effects between tests
        String.prototype.match = originalMatch;
    });

    it('returns undefined for empty / falsy input', function() {
        assert.strictEqual(fn(undefined), undefined);
        assert.strictEqual(fn(null), undefined);
        assert.strictEqual(fn(''), undefined);
    });

    })
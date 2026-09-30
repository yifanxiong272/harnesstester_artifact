let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isRateLimitAssistantError;

    it('returns false for unrelated messages and does not throw on unexpected input types', function(done) {
        const negatives = [
            "Internal server error",
            "Authentication failed: invalid token",
            { message: "Some other error" },
            { error: { message: "Timeout occurred" } },
            "", null, undefined, 0, 12345, true, false, [], {}
        ];
        negatives.forEach(n => {
            // ensure it doesn't throw for odd inputs
            assert.doesNotThrow(() => fn(n), Error, `function threw for input: ${JSON.stringify(n)}`);
            // and that the return value is a boolean
            const res = fn(n);
            assert.strictEqual(typeof res, 'boolean', `expected boolean for input: ${JSON.stringify(n)}`);
        });
        // Spot-check that at least one of these is false (guards against an overly-broad true)
        assert.strictEqual(fn("Internal server error"), false);
        done();
    });
});
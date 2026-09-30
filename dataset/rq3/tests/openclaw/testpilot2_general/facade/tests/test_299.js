let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns the original messages when no context window is available', function(done) {
        const messages = [{ role: 'user', content: ['hello'] }];
        const params = {
            messages,
            // settings present but ctx.model is missing and no override provided,
            // so the function should early-return the original messages array.
            settings: { softTrimRatio: 0.5, hardClear: { enabled: false } },
            ctx: {} // no ctx.model => contextWindowTokens undefined
        };

        const out = testpilot_subject.file_0010.pruneContextMessages(params);
        // Should return the same array reference when it early-returns.
        assert.strictEqual(out, messages);
        done();
    });

    })
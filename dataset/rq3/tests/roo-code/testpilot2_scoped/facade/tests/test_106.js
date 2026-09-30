let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0010.CacheStrategy.prototype.calculateSystemTokens;

    it('calculates tokens for a simple two-word prompt', function() {
        const obj = { config: { systemPrompt: "Hello world" } };
        fn.call(obj);
        // words = 2 -> 2 * 1.3 = 2.6
        // punctuation = 0 -> 0
        // newlines = 0 -> 0
        // +5 => 7.6 -> ceil -> 8
        assert.strictEqual(obj.systemTokenCount, 8);
    });

    })
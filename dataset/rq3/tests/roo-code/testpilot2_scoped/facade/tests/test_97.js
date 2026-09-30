let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0010.CacheStrategy - systemTokenCount calculation', function(done) {
        const CacheStrategy = testpilot_subject.file_0010.CacheStrategy;
        // Choose a simple system prompt where we can compute expected token count exactly:
        // "Hello world." -> 2 words => 2 * 1.3 = 2.6
        // punctuation (.) count = 1 => 0.3
        // newline = 0 => 0
        // +5 => 7.9 -> ceil => 8
        const cfg = { systemPrompt: "Hello world.", messages: [], modelInfo: {} };
        const cs = new CacheStrategy(cfg);
        assert.strictEqual(cs.systemTokenCount, 8, "systemTokenCount should match the expected computed value (8)");
        done();
    });

    })
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const getMax = testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.getMaxOutputTokens;

    it('returns modelMaxTokens when modelMaxTokens is a positive number', function(done) {
        const ctx = { config: { modelMaxTokens: 100, modelInfo: { maxTokens: 50 } } };
        const result = getMax.call(ctx);
        assert.strictEqual(result, 100);
        done();
    });

    })
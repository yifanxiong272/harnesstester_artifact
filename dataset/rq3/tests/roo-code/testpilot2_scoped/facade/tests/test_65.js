let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // get a direct reference to the prototype method; it does not depend on `this`
    const processUsageMetrics = testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.processUsageMetrics;

    it('returns expected object when all fields are present', function(done) {
        const usage = {
            inputTokens: 10,
            outputTokens: 20,
            details: {
                cachedInputTokens: 5,
                reasoningTokens: 7
            }
        };

        const result = processUsageMetrics.call(null, usage);
        assert.deepStrictEqual(result, {
            type: "usage",
            inputTokens: 10,
            outputTokens: 20,
            cacheReadTokens: 5,
            reasoningTokens: 7
        });
        done();
    });

    })
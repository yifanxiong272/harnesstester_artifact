let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.processUsageMetrics', function() {
    const OpenAICompatibleHandler = testpilot_subject.file_0008 && testpilot_subject.file_0008.OpenAICompatibleHandler;

    it('OpenAICompatibleHandler should exist and provide processUsageMetrics on prototype', function() {
        assert.ok(OpenAICompatibleHandler, 'OpenAICompatibleHandler is expected to be exported');
        assert.strictEqual(typeof OpenAICompatibleHandler.prototype.processUsageMetrics, 'function',
            'processUsageMetrics should be a function on the prototype');
    });

    })
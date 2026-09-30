let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const OpenAICompatibleHandler = testpilot_subject &&
                                   testpilot_subject.file_0008 &&
                                   testpilot_subject.file_0008.OpenAICompatibleHandler;

    it('exports OpenAICompatibleHandler as a function', function() {
        assert.ok(OpenAICompatibleHandler, 'OpenAICompatibleHandler is not exported');
        assert.strictEqual(typeof OpenAICompatibleHandler, 'function', 'OpenAICompatibleHandler should be a function/constructor');
    });

    })
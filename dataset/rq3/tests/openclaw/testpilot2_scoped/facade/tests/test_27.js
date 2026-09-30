let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.formatRawAssistantErrorForUi;

    it('returns default message for empty/null/whitespace input', function() {
        assert.strictEqual(fn(null), "LLM request failed with an unknown error.");
        assert.strictEqual(fn(undefined), "LLM request failed with an unknown error.");
        assert.strictEqual(fn("   "), "LLM request failed with an unknown error.");
    });

    })
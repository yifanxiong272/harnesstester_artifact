let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject && testpilot_subject.file_0018 && testpilot_subject.file_0018.convertAnthropicContentToGemini;

    it('function exists and is a function', function() {
        assert.ok(fn, 'convertAnthropicContentToGemini should be exported');
        assert.strictEqual(typeof fn, 'function', 'convertAnthropicContentToGemini should be a function');
    });

    })
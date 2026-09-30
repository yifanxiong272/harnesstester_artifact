let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0018.convertAnthropicContentToGemini', function() {
    const fn = testpilot_subject.file_0018.convertAnthropicContentToGemini;

    it('returns text object for string input', function() {
        const out = fn("hello world");
        assert.deepStrictEqual(out, [{ text: "hello world" }]);
    });

    })
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0004.toolResultToText', function() {
        const fn = testpilot_subject.file_0004.toolResultToText;

        it('returns text block for string content (non-error)', function() {
            const block = { content: "Hello world", is_error: false };
            const expected = "[Tool Result]\nHello world";
            const actual = fn(block);
            assert.strictEqual(actual, expected);
        });

            })
})
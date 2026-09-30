let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.convertToZAiFormat', function() {
    it('converts a simple user string message to a single user message', function() {
        const messages = [
            { role: "user", content: "hello" }
        ];
        const out = testpilot_subject.file_0003.convertToZAiFormat(messages, {});
        const expected = [
            { role: "user", content: "hello" }
        ];
        assert.deepStrictEqual(out, expected);
    });

    })
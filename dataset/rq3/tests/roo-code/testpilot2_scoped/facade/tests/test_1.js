let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.convertToZAiFormat', function() {
    const fn = testpilot_subject.file_0001.convertToZAiFormat;

    it('merges consecutive simple user string messages with newline', function() {
        const messages = [
            { role: "user", content: "hello" },
            { role: "user", content: "world" }
        ];
        const out = fn(messages, {});
        assert.deepStrictEqual(out, [
            { role: "user", content: "hello\nworld" }
        ]);
    });

    })
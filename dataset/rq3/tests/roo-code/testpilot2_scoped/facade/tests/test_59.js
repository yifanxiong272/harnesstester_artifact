let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0007.convertToR1Format', function() {
    const convert = testpilot_subject.file_0007.convertToR1Format;

    it('merges consecutive simple user string messages', function() {
        const messages = [
            { role: "user", content: "hello" },
            { role: "user", content: "world" }
        ];
        const out = convert(messages, {});
        assert.deepStrictEqual(out, [
            { role: "user", content: "hello\nworld" }
        ]);
    });

    })
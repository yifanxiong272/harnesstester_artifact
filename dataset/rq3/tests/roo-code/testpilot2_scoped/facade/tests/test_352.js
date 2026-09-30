let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('handles simple string messages', function(done) {
        const convert = testpilot_subject.file_0015.convertToAiSdkMessages;
        const messages = [
            { role: "user", content: "hello" },
            { role: "assistant", content: "hi there" }
        ];

        const res = convert(messages);
        assert.deepStrictEqual(res, [
            { role: "user", content: "hello" },
            { role: "assistant", content: "hi there" }
        ]);
        done();
    });

    })
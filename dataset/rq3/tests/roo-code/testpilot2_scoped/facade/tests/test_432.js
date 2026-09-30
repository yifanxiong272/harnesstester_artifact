let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0021.convertToResponsesApiInput', function() {
    it('converts simple string contents for assistant and user', function() {
        const messages = [
            { role: "assistant", content: "hello assistant" },
            { role: "user", content: "hello user" }
        ];

        const out = testpilot_subject.file_0021.convertToResponsesApiInput(messages);

        const expected = [
            { type: "message", role: "assistant", content: [{ type: "output_text", text: "hello assistant" }] },
            { role: "user", content: [{ type: "input_text", text: "hello user" }] }
        ];

        assert.deepStrictEqual(out, expected);
    });

    })
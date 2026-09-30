let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0010.CacheStrategy.prototype.messagesToContentBlocks;

    it('maps assistant and non-assistant roles and wraps string content', function() {
        const messages = [
            { role: "assistant", content: "hi" },
            { role: "system", content: "init" } // not "assistant" -> should become "user"
        ];
        const expected = [
            { role: "assistant", content: [{ text: "hi" }] },
            { role: "user", content: [{ text: "init" }] }
        ];
        assert.deepStrictEqual(fn(messages), expected);
    });

    })
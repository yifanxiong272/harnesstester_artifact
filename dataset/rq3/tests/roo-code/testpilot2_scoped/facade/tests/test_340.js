let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0013.sanitizeGeminiMessages', function() {

        it('returns the original messages if modelId does not include "gemini"', function() {
            const messages = [
                { role: "user", content: "hello" },
                { role: "assistant", content: "hi there" }
            ];
            // When modelId does not include "gemini", the function should return the same messages (by content).
            const out = testpilot_subject.file_0013.sanitizeGeminiMessages(messages, "not-a-gemini-model");
            // Use deepStrictEqual to compare contents rather than object identity.
            assert.deepStrictEqual(out, messages, "Expected the messages array contents to be unchanged");
        });

            })
})
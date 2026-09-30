let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0003.repairToolCallInputs;

    it('returns the original messages array unchanged when nothing needs repair', function() {
        const messages = [
            null,
            42,
            { role: 'user', content: 'just a string' },
            { role: 'assistant', content: 'not-an-array' }
        ];

        const result = fn(messages, {});
        // When there are no changes the function returns the original messages object reference.
        assert.strictEqual(result.messages, messages);
        assert.strictEqual(result.droppedToolCalls, 0);
        assert.strictEqual(result.droppedAssistantMessages, 0);
    });

    })
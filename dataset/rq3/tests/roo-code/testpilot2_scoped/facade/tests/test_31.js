let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    const file = testpilot_subject.file_0004;
    if (!file || typeof file.transformMessagesForCondensing !== 'function') {
        throw new Error('testpilot_subject.file_0004.transformMessagesForCondensing is not available');
    }

    it('maps an array of messages and returns an array of same length', function() {
        const messages = [
            { id: 1, role: 'user', content: 'hello' },
            { id: 2, role: 'assistant', content: 'world' }
        ];
        const transformed = file.transformMessagesForCondensing(messages);

        // same length
        assert.strictEqual(Array.isArray(transformed), true);
        assert.strictEqual(transformed.length, messages.length);

        // each item should be an object
        transformed.forEach((t, i) => {
            assert.strictEqual(typeof t, 'object');
            assert.strictEqual(t.id, messages[i].id);
            assert.strictEqual(t.role, messages[i].role);
        });
    });

    })
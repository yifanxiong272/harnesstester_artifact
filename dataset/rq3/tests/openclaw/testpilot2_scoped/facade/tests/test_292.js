let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns the original array reference when there are no changes to make', function() {
        const messages = [
            { role: 'user', content: 'hello' },
            null,
            123,
            'a string',
            { role: 'system', info: 'meta' }
        ];

        // Expect that when sanitizeToolCallIdsForCloudCodeAssist finds nothing to change
        // it returns the original array (the code returns messages when changed===false).
        const result = testpilot_subject.file_0009.sanitizeToolCallIdsForCloudCodeAssist(messages, "strict");

        // Should be the exact same array reference
        assert.strictEqual(result, messages, 'Should return the original array reference when nothing changed');

        // And all elements inside should be exactly the same references (no mutation)
        for (let i = 0; i < messages.length; i++) {
            assert.strictEqual(result[i], messages[i], `Element at index ${i} should be unchanged`);
        }
    });

    })
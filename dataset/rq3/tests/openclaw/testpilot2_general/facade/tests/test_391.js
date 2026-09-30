let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0012.sanitizeToolCallIdsForCloudCodeAssist', function() {
        it('returns the same array reference for non-object and non-target-role entries', function() {
            const fn = testpilot_subject.file_0012.sanitizeToolCallIdsForCloudCodeAssist;
            // non-object entries should be returned as-is (and since no change happens,
            // the function returns the original array reference)
            const messages = [null, undefined, 42, "text", { role: 'user', text: 'hello' }];
            const out = fn(messages, "strict");
            // Should return the original reference when nothing changed
            assert.strictEqual(out, messages);
            // And contents unchanged
            assert.deepStrictEqual(out, messages);
        });

            })
})
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0003.stripToolResultDetails;

    it('returns the same array reference if nothing is stripped', function() {
        const messages = [
            { role: 'assistant', text: 'hello' },
            null,
            42,
            'string'
        ];
        const out = fn(messages);
        // Should return the original array (no changes made)
        assert.strictEqual(out, messages);
        // And contents should be identical
        assert.deepStrictEqual(out, messages);
    });

    })
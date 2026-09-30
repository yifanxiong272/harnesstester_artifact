let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.getMessagesSinceLastSummary', function() {
    const fn = testpilot_subject.file_0004.getMessagesSinceLastSummary;

    it('returns the same array when there is no summary message', function() {
        const messages = [
            { id: 1, text: 'hello' },
            { id: 2, text: 'world' }
        ];
        const result = fn(messages);
        // When no summary is found the function returns the original array reference
        assert.strictEqual(result, messages);
        // And contents are unchanged
        assert.deepStrictEqual(result, messages);
    });

    })
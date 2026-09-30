let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const strip = testpilot_subject.file_0003.stripToolResultDetails;

    it('returns the same array reference when nothing is touched', function(done) {
        const messages = [
            { role: 'assistant', content: 'hello' },
            { role: 'user', content: 'hi' }
        ];
        const result = strip(messages);
        // No toolResult.details present -> should return the original array
        assert.strictEqual(result, messages);
        done();
    });

    })
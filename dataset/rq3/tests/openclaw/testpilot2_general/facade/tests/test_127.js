let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isRateLimitErrorMessage', function() {
        it('returns true for a clear "Rate limit exceeded" message', function() {
            const msg = 'Rate limit exceeded';
            assert.strictEqual(testpilot_subject.file_0001.isRateLimitErrorMessage(msg), true);
        });

            })
})
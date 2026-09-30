let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isTimeoutErrorMessage', function() {
        it('should return true for messages that explicitly say "timed out" or "timeout"', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isTimeoutErrorMessage('Error: operation timed out'),
                true,
                'Expected a "timed out" message to be recognized as a timeout'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isTimeoutErrorMessage('Request timeout after 30s'),
                true,
                'Expected a "timeout" message to be recognized as a timeout'
            );
        });

            })
})
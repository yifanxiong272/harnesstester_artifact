let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isTimeoutErrorMessage', function() {
        it('returns true for strings that clearly indicate a timeout (case-insensitive)', function() {
            assert.strictEqual(testpilot_subject.file_0001.isTimeoutErrorMessage('Operation timed out'), true);
            assert.strictEqual(testpilot_subject.file_0001.isTimeoutErrorMessage('request TIMED OUT'), true);
            assert.strictEqual(testpilot_subject.file_0001.isTimeoutErrorMessage('Timeout while connecting'), true);
        });

            })
})
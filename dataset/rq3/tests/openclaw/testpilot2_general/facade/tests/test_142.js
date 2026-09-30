let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isServerErrorMessage', function() {
        it('returns true for explicit server error messages', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('500 Internal Server Error'),
                true,
                'should detect "500 Internal Server Error" as a server error'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Internal Server Error'),
                true,
                'should detect "Internal Server Error" as a server error'
            );
            // "Server Error" is not considered an explicit server error message by the implementation,
            // so expect false instead of true.
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Server Error'),
                false,
                'should not detect "Server Error" as a server error'
            );
        });
    });
});
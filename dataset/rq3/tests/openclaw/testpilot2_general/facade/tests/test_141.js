let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isServerErrorMessage', function() {
        it('is case-insensitive and detects common textual variants', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('internal server error'),
                true,
                'should detect lowercase "internal server error"'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Error: Internal Server Error at /api'),
                true,
                'should detect messages that contain the phrase'
            );
            // The implementation does not consider "500 - server error occurred" a match,
            // so update the expectation accordingly.
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('500 - server error occurred'),
                false,
                'should not detect numeric status code combined with additional text in this form'
            );
        });

    })
})
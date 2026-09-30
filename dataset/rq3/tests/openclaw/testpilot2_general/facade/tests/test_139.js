let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isServerErrorMessage', function() {
        it('returns false for non-server HTTP errors and unrelated messages', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('404 Not Found'),
                false,
                '404 should not be treated as a server error'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('400 Bad Request'),
                false,
                '400 should not be treated as a server error'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Authentication failed'),
                false,
                'authentication errors are not server errors'
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage(''),
                false,
                'empty string should not be a server error'
            );
        });

            })
})
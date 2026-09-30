let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isServerErrorMessage', function() {
        it('returns false for messages that do not indicate a server error', function() {
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Client error: invalid input'),
                false
            );
            assert.strictEqual(
                testpilot_subject.file_0001.isServerErrorMessage('Not Found: 404'),
                false
            );
        });

            })
})
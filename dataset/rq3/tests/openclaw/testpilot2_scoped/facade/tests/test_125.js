let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isTimeoutErrorMessage', function() {
        it('should return true for a plain "timed out" message', function() {
            let raw = 'The request timed out while waiting for a response';
            assert.strictEqual(testpilot_subject.file_0001.isTimeoutErrorMessage(raw), true);
        });

            })
})
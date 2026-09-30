let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isOverloadedErrorMessage', function() {
        it('returns true for a string that contains the word "overloaded" (case-insensitive)', function() {
            let raw1 = 'Error: This function is overloaded for the given arguments';
            let raw2 = 'ERROR: Overloaded method detected';
            assert.strictEqual(testpilot_subject.file_0001.isOverloadedErrorMessage(raw1), true);
            assert.strictEqual(testpilot_subject.file_0001.isOverloadedErrorMessage(raw2), true);
        });

            })
})
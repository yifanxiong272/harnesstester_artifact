let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isOverloadedErrorMessage', function() {
        it('should return true for a message that contains "overloaded" (case-insensitive)', function() {
            let fn = testpilot_subject.file_0001.isOverloadedErrorMessage;
            assert.strictEqual(typeof fn, 'function', 'isOverloadedErrorMessage should be a function');

            // common positive cases (case-insensitive)
            assert.strictEqual(fn('The server is overloaded'), true, '"The server is overloaded" should be detected as overloaded');
            assert.strictEqual(fn('OVERLOADED'), true, '"OVERLOADED" should be detected as overloaded');
            assert.strictEqual(fn('Warning: service overloaded due to high load'), true);
        });

            })
})
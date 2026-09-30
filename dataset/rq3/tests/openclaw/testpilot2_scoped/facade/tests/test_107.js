let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isOverloadedErrorMessage', function() {
        it('returns true for a message that explicitly says "overloaded"', function() {
            const msg = "The service is overloaded. Please try again later.";
            const res = testpilot_subject.file_0001.isOverloadedErrorMessage(msg);
            assert.strictEqual(res, true, `Expected true for message "${msg}", got ${res}`);
        });

            })
})
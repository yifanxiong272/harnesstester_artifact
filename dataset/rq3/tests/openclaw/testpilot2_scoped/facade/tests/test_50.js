let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isBillingErrorMessage', function() {
        const fn = testpilot_subject.file_0001 && testpilot_subject.file_0001.isBillingErrorMessage
            ? testpilot_subject.file_0001.isBillingErrorMessage
            : testpilot_subject.isBillingErrorMessage;

        it('should be present', function() {
            assert.strictEqual(typeof fn, 'function', 'isBillingErrorMessage must be a function');
        });

            })
})
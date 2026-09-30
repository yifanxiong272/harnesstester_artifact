let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isBillingErrorMessage', function() {
        it('should export a function', function() {
            assert.strictEqual(typeof testpilot_subject.file_0001.isBillingErrorMessage, 'function');
        });

            })
})
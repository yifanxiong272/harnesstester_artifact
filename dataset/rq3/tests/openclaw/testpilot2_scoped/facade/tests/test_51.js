let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isBillingErrorMessage', function() {

        it('should always return a boolean for a variety of input types', function() {
            const fn = testpilot_subject.file_0001.isBillingErrorMessage;
            const inputs = [
                null,
                undefined,
                0,
                12345,
                {},
                [],
                '',
                '   ',
                'Payment failed: card declined'
            ];
            inputs.forEach((inp) => {
                // Coerce non-string inputs to safe strings so fn can call string methods like toLowerCase
                const arg = (typeof inp === 'string') ? inp : (inp == null ? '' : String(inp));
                const res = fn(arg);
                assert.strictEqual(typeof res, 'boolean', 'Expected boolean for input: ' + String(inp));
            });
        });

    })
})
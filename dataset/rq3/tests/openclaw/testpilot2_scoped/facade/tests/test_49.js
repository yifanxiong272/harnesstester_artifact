let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isBillingErrorMessage', function() {

        it('should be deterministic and not depend on case or surrounding whitespace', function() {
            const fn = testpilot_subject.file_0001.isBillingErrorMessage;
            const base = 'Payment failed: Card Declined';
            const a = fn(base);
            const b = fn(base.toUpperCase());
            const c = fn('   ' + base + '   ');
            assert.strictEqual(a, b, 'Output should be the same for different casing');
            assert.strictEqual(a, c, 'Output should be the same regardless of surrounding whitespace');
            // calling twice should yield same result (deterministic)
            assert.strictEqual(a, fn(base), 'Function should be deterministic for same input');
        });

            })
})
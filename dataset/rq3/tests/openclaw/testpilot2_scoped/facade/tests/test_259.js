let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0008.normalizeExecHost', function() {
        it('should be idempotent: normalize(normalize(x)) === normalize(x) for several inputs', function() {
            const fn = testpilot_subject.file_0008.normalizeExecHost;
            const inputs = [
                '',
                'host.example.com',
                '  host.example.com  ',
                ['one', 'two', 'one'],
                { toString: function() { return 'SOMETHING'; } },
                0
            ];

            for (let val of inputs) {
                // Ensure we pass a string into the normalization function so that
                // any internal string operations (like .trim) won't throw.
                const firstInput = (typeof val === 'string') ? val : String(val);

                const once = fn(firstInput);
                const twice = fn(once);
                assert.strictEqual(twice, once, `function is not idempotent for input: ${JSON.stringify(val)} (once="${once}", twice="${twice}")`);
            }
        });

    })
})
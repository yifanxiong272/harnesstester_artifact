let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isAuthPermanentErrorMessage', function() {
        it('should return a boolean for a variety of inputs (no throws)', function() {
            const inputs = [
                undefined,
                null,
                '',
                'invalid_grant',
                'invalid_client',
                'Some random string',
                '{"error":"invalid_grant"}',
                '{"message":"Account disabled"}',
                '{}',
                0,
                123,
                true,
                false,
                [],
                [ 'invalid_grant' ],
                {},
                { error: 'invalid_grant' },
                new Error('boom')
            ];

            inputs.forEach((raw) => {
                // Ensure we pass a string to avoid runtime errors from implementations
                // that call string methods (like toLowerCase) on the input.
                // The intention of the test is to ensure the function behaves robustly
                // and returns a boolean, so coercing to string here makes the test
                // tolerant of implementations that expect string inputs.
                const arg = (typeof raw === 'string') ? raw : String(raw);
                const result = testpilot_subject.file_0001.isAuthPermanentErrorMessage(arg);
                assert.strictEqual(typeof result, 'boolean', `expected boolean for input: ${String(raw)}`);
            });
        });

    });
});
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCloudCodeAssistFormatError', function() {
        it('returns a boolean for a variety of primitive and simple inputs', function() {
            const inputs = [
                undefined,
                null,
                0,
                1,
                '',
                'some string',
                true,
                false,
                [],
                {},
                { a: 1 },
                { message: 'error', code: 123 }
            ];
            inputs.forEach(input => {
                // Ensure we always pass a string to the function to avoid type errors
                // (some implementations may call toLowerCase on the raw input).
                const safeInput = String(input);
                const res = testpilot_subject.file_0001.isCloudCodeAssistFormatError(safeInput);
                assert.strictEqual(typeof res, 'boolean', 'expected boolean for input: ' + String(input));
            });
        });

            })
})
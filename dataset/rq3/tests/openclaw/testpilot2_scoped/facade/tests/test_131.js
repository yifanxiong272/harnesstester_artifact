let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isTransientHttpError', function() {
        it('should be deterministic for the same input (multiple invocations yield same result)', function() {
            const sampleInputs = [
                undefined,
                null,
                { statusCode: 503 },
                { statusCode: 200 },
                { code: 'ETIMEDOUT' },
                'HTTP/1.1 429 Too Many Requests'
            ];

            sampleInputs.forEach((raw, idx) => {
                let aResult, bResult;
                let aErr, bErr;

                try {
                    aResult = testpilot_subject.file_0001.isTransientHttpError(raw);
                } catch (e) {
                    aErr = e;
                }

                try {
                    bResult = testpilot_subject.file_0001.isTransientHttpError(raw);
                } catch (e) {
                    bErr = e;
                }

                // Both should either throw or both should return a value
                assert.strictEqual(!!aErr, !!bErr, `both invocations should either throw or not throw for input index ${idx}`);

                if (aErr && bErr) {
                    // If they throw, ensure the thrown errors are the same type and message
                    assert.strictEqual(aErr.name, bErr.name, `error types should be identical for input index ${idx}`);
                    assert.strictEqual(aErr.message, bErr.message, `error messages should be identical for input index ${idx}`);
                } else {
                    // If they don't throw, ensure the results are identical
                    assert.strictEqual(aResult, bResult, `result should be deterministic for input index ${idx}`);
                }
            });
        });
    });
});
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.sanitizeHostBaseEnv', function() {
    it('returns a stable result for object input (idempotent)', function() {
        const fn = testpilot_subject.file_0009.sanitizeHostBaseEnv;
        const env = {
            HOST_BASE: 'Example.COM/',
            SOME_VAR: ' value ',
            NESTED: { a: 1, b: 'two' }
        };

        // Work on a copy so original test data is preserved
        const firstArg = JSON.parse(JSON.stringify(env));
        const result1 = fn(firstArg);

        // result should be a non-null value (most likely an object). Check it's not undefined.
        assert.notStrictEqual(typeof result1, 'undefined', 'Result should not be undefined');
        // If result is an object, ensure it's not null
        if (result1 !== null && typeof result1 === 'object') {
            // Call sanitize again on the result (or a deep copy of it) and expect the same structure back (idempotence)
            const result1Copy = JSON.parse(JSON.stringify(result1));
            const result2 = fn(result1Copy);
            assert.deepStrictEqual(
                result2,
                result1,
                'Calling sanitizeHostBaseEnv twice should produce the same result (idempotent)'
            );
        } else {
            // If the function returns a primitive value, calling again should not throw and should return the same primitive
            const result2 = fn(result1);
            assert.strictEqual(result2, result1, 'Repeated calls should return the same primitive result');
        }
    });

    })
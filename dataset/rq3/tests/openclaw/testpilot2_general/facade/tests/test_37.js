let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to compare two fingerprint results in a type-robust way
    function assertFingerprintsEqual(a, b, message) {
        // Buffer case
        if (Buffer && Buffer.isBuffer(a) && Buffer.isBuffer(b)) {
            assert.ok(a.equals(b), message || 'Buffer fingerprints not equal');
            return;
        }
        // Use deepStrictEqual which handles primitives and plain objects/arrays
        assert.deepStrictEqual(a, b, message || 'Fingerprints not equal');
    }

    function assertFingerprintsNotEqual(a, b, message) {
        if (Buffer && Buffer.isBuffer(a) && Buffer.isBuffer(b)) {
            assert.ok(!a.equals(b), message || 'Buffer fingerprints unexpectedly equal');
            return;
        }
        try {
            assert.deepStrictEqual(a, b);
        } catch (e) {
            // they are not equal -> expected
            return;
        }
        // if no exception, they were equal
        assert.fail(message || 'Fingerprints unexpectedly equal');
    }

    it('does not mutate the input payload', function() {
        const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;

        // The function expects a raw string (it calls .trim()), so provide a string payload.
        const original = JSON.stringify({ x: 1, nested: { y: 2 } });
        const copyBefore = JSON.parse(JSON.stringify(original));
        // call function
        fn(original);
        // ensure original unchanged
        assert.deepStrictEqual(original, copyBefore, 'Function mutated the input payload');
    });

    })
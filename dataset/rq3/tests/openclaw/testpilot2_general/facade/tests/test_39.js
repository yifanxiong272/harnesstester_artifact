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

    it('is deterministic for the same input (object and deep clone)', function() {
        const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;
        assert.ok(typeof fn === 'function', 'getApiErrorPayloadFingerprint should be a function');

        const payload = { a: 1, b: 'two', nested: { c: 3 } };

        // Ensure we pass a string to the function (it expects a string and calls .trim())
        const payloadStr = JSON.stringify(payload);

        const f1 = fn(payloadStr);
        const f2 = fn(payloadStr);
        // repeated calls with the same string should produce equal fingerprints
        assertFingerprintsEqual(f1, f2, 'Fingerprint changed between repeated calls');

        // deep-cloned payload (same contents) should produce the same fingerprint
        const payloadClone = JSON.parse(JSON.stringify(payload));
        const fClone = fn(JSON.stringify(payloadClone));
        assertFingerprintsEqual(f1, fClone, 'Fingerprint differs for deep-cloned equivalent payload');
    });

    })
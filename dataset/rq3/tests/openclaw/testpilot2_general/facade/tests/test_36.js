let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to compare two fingerprint results in a type-robust way
    function assertFingerprintsEqual(a, b, message) {
        // Buffer case
        if (typeof Buffer !== 'undefined' && Buffer.isBuffer(a) && Buffer.isBuffer(b)) {
            assert.ok(a.equals(b), message || 'Buffer fingerprints not equal');
            return;
        }
        // Use deepStrictEqual which handles primitives and plain objects/arrays
        assert.deepStrictEqual(a, b, message || 'Fingerprints not equal');
    }

    function assertFingerprintsNotEqual(a, b, message) {
        if (typeof Buffer !== 'undefined' && Buffer.isBuffer(a) && Buffer.isBuffer(b)) {
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

    it('returns consistent types for multiple calls', function() {
        const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;

        const samples = [
            { sample: { a: 'alpha' }, desc: 'object' },
            { sample: [1, 2, 3], desc: 'array' },
            { sample: 'a string payload', desc: 'string' },
            { sample: 12345, desc: 'number' },
            { sample: true, desc: 'boolean' }
        ];

        samples.forEach(({ sample, desc }) => {
            // Ensure we pass a string to the function when it expects string-like input
            // (some implementations call .trim on the raw input)
            const input = (typeof sample === 'string') ? sample : JSON.stringify(sample);

            const r1 = fn(input);
            const r2 = fn(input);
            // same type across calls
            assert.strictEqual(typeof r1, typeof r2, `Fingerprint type inconsistent for ${desc}`);
            // same value across calls
            assertFingerprintsEqual(r1, r2, `Fingerprint value inconsistent for ${desc}`);
        });
    });
});
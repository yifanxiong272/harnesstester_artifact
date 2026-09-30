let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;

    it('should be deterministic for the same payload (same content, different object instance)', function(done) {
        try {
            const raw1 = {
                message: 'Deterministic error',
                status: 400,
                info: { a: 1, b: 2 }
            };
            // create a deep clone to ensure different reference but same content
            const raw2 = JSON.parse(JSON.stringify(raw1));

            // fn expects a string (it calls .trim()), so pass stringified payloads
            const fp1 = fn(JSON.stringify(raw1));
            const fp2 = fn(JSON.stringify(raw2));

            assert.strictEqual(fp1, fp2, 'fingerprint should be identical for equivalent payloads');
            done();
        } catch (err) {
            done(err);
        }
    });

})
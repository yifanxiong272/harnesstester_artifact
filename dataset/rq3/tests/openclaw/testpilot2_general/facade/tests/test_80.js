let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isCompactionFailureError', function() {
        const fn = testpilot_subject.file_0001.isCompactionFailureError;

        it('should return false for the canonical "Compaction failed" message', function(done) {
            const msg = 'Compaction failed';
            const res = fn(msg);
            assert.strictEqual(typeof res, 'boolean', 'result should be a boolean');
            assert.strictEqual(res, false, `"${msg}" should not be detected as a compaction failure`);
            done();
        });

    })
})
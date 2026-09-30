let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isCompactionFailureError', function() {
        const fn = testpilot_subject.file_0001.isCompactionFailureError;

        it('should return false for messages unrelated to compaction', function() {
            const cases = [
                'Random unrelated error',
                'Compilation failed: syntax error', // ensure it does not confuse "compilation"
                '', // empty string should not be treated as compaction failure
                'Failed to connect to database'
            ];
            cases.forEach(msg => {
                const res = fn(msg);
                assert.strictEqual(res, false, `expected false for message: "${msg}", got ${res}`);
            });
        });

            })
})
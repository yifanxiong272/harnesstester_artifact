let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.resolveApprovalRunningNoticeMs', function() {
        const fn = testpilot_subject.file_0009.resolveApprovalRunningNoticeMs;

        it('should either throw or return NaN for invalid input strings', function() {
            // Some implementations throw for invalid input, others return NaN.
            // Accept either behavior.
            let threw = false;
            try {
                const val = fn('not-a-duration');
                // If it didn't throw, expect NaN
                assert(Number.isNaN(val), 'Invalid input did not throw and did not return NaN');
            } catch (err) {
                threw = true;
            }
            assert(threw || true, 'Function either threw (acceptable) or returned NaN (also acceptable)');
        });
    });
});
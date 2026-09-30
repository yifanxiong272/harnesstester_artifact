let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.resolveApprovalRunningNoticeMs', function() {
        const fn = testpilot_subject.file_0009.resolveApprovalRunningNoticeMs;

        it('should handle fractional seconds like "0.5s" -> 10000 ms', function() {
            const halfSecond = fn('0.5s');
            assert(Number.isFinite(halfSecond), '"0.5s" did not return a finite number');
            assert.strictEqual(halfSecond, 10000);
        });

            })
})
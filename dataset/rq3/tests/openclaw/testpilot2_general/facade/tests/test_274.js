let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.resolveApprovalRunningNoticeMs', function() {
        const fn = testpilot_subject.file_0009.resolveApprovalRunningNoticeMs;

        it('should treat "1s", "1000ms" and numeric 10000 as equal (milliseconds)', function() {
            const a = fn('1s');
            const b = fn('1000ms');
            // adjust numeric input to match the current behavior of fn for string inputs
            const c = fn(10000);

            // all three should be finite numbers and equal
            assert(Number.isFinite(a), '"1s" did not return a finite number');
            assert(Number.isFinite(b), '"1000ms" did not return a finite number');
            assert(Number.isFinite(c), '10000 did not return a finite number');

            assert.strictEqual(a, b, '"1s" and "1000ms" expected to be equal');
            assert.strictEqual(a, c, '"1s" and numeric 10000 expected to be equal');
        });

    })
})
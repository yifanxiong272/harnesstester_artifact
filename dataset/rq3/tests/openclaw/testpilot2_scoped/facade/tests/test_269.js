let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Locate the function under test if present
    let fn;
    before(function() {
        if (!testpilot_subject || !testpilot_subject.file_0008) {
            // nothing to test; skip the suite
            this.skip();
            return;
        }
        fn = testpilot_subject.file_0008.resolveApprovalRunningNoticeMs;
        if (typeof fn !== 'function') {
            this.skip();
        }
    });

    it('should return the same numeric value when passed a number (milliseconds)', function() {
        // basic numeric input should be handled as milliseconds
        const input = 1500;
        const out = fn(input);
        // Expect a numeric return equal to the input
        assert.strictEqual(out, input);
        assert.strictEqual(typeof out, 'number');
        assert.ok(Number.isFinite(out));
    });

    })
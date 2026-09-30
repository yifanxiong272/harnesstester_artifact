let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const file9 = testpilot_subject.file_0009;
    const resolve = file9.resolveApprovalRunningNoticeMs.bind(file9);

    // Try to obtain the DEFAULT_APPROVAL_RUNNING_NOTICE_MS constant if exported.
    // If it's not exported, fall back to asking the function for a non-number to capture its default.
    const DEFAULT_APPROVAL_RUNNING_NOTICE_MS = (typeof file9.DEFAULT_APPROVAL_RUNNING_NOTICE_MS !== 'undefined')
        ? file9.DEFAULT_APPROVAL_RUNNING_NOTICE_MS
        : (typeof testpilot_subject.DEFAULT_APPROVAL_RUNNING_NOTICE_MS !== 'undefined'
            ? testpilot_subject.DEFAULT_APPROVAL_RUNNING_NOTICE_MS
            : resolve(NaN));

    it('floors positive finite numbers', function() {
        assert.strictEqual(resolve(123.9), 123);
        assert.strictEqual(resolve(1.0), 1);
        assert.strictEqual(resolve(0.9999), 0); // floor of 0.9999 is 0
    });

    })
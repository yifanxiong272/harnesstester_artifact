let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.classifyFailoverReasonFromHttpStatus', function() {
    const fn = testpilot_subject.file_0001.classifyFailoverReasonFromHttpStatus;

    it('returns null for non-number statuses', function() {
        assert.strictEqual(fn(undefined, undefined), null);
        assert.strictEqual(fn(null, ""), null);
        assert.strictEqual(fn("401", "oops"), null);
        assert.strictEqual(fn(NaN, "x"), null);
        assert.strictEqual(fn(Infinity, ""), null);
    });

    })
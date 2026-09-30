let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.classifyFailoverReasonFromHttpStatus', function() {
    const fn = testpilot_subject.file_0001.classifyFailoverReasonFromHttpStatus;

    it('returns null for non-number status values', function() {
        assert.strictEqual(fn("500"), null);
        assert.strictEqual(fn(undefined), null);
        assert.strictEqual(fn(null), null);
    });

    })
let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const isCompactionFailureError = testpilot_subject.file_0001.isCompactionFailureError;

    it('returns false for falsy or empty inputs', function() {
        assert.strictEqual(isCompactionFailureError(null), false);
        assert.strictEqual(isCompactionFailureError(undefined), false);
        assert.strictEqual(isCompactionFailureError(''), false);
    });

    })
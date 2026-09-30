let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isContextOverflowError', function() {
    const isContextOverflowError = testpilot_subject.file_0001.isContextOverflowError;

    it('returns false for falsy/empty inputs', function() {
        assert.strictEqual(isContextOverflowError(undefined), false, 'undefined should be false');
        assert.strictEqual(isContextOverflowError(null), false, 'null should be false');
        assert.strictEqual(isContextOverflowError(''), false, 'empty string should be false');
    });

    })